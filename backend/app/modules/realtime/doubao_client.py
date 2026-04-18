"""Async Doubao Realtime Dialogue WebSocket client.

Connects to `wss://openspeech.bytedance.com/api/v3/realtime/dialogue` using the
Volcengine-issued credentials, frames client events via `doubao_protocol`, and
yields decoded server frames to the caller.

This module does **not** know about FastAPI, Supabase, or our DB — it only
speaks the Doubao wire protocol. The proxy layer (`doubao_proxy.py`) is what
glues this client to a frontend WebSocket session.
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from dataclasses import dataclass, field
from typing import AsyncIterator, Final

from app.modules.realtime.doubao_protocol import (
    ClientEvent,
    DoubaoFrame,
    build_audio_client_frame,
    build_json_client_frame,
    decode_frame,
)

try:
    import websockets
    from websockets.client import WebSocketClientProtocol
    from websockets.exceptions import ConnectionClosed
except ImportError:  # pragma: no cover - exercised only when `websockets` is missing locally
    websockets = None  # type: ignore[assignment]
    WebSocketClientProtocol = object  # type: ignore[misc, assignment]
    ConnectionClosed = Exception  # type: ignore[misc, assignment]


logger = logging.getLogger(__name__)

DEFAULT_WS_URL: Final[str] = "wss://openspeech.bytedance.com/api/v3/realtime/dialogue"
DEFAULT_RESOURCE_ID: Final[str] = "volc.speech.dialog"
# Per Doubao docs: fixed app key for the realtime dialogue resource.
DEFAULT_APP_KEY: Final[str] = "PlgvMymc7f3tQnJ6"

# Client audio upload: PCM16 / 16 kHz / mono / little-endian / 20ms-per-packet
DEFAULT_INPUT_SAMPLE_RATE: Final[int] = 16000
DEFAULT_INPUT_CHANNELS: Final[int] = 1
DEFAULT_INPUT_BITS: Final[int] = 16

# Server TTS output we want back: pcm_s16le / 24 kHz / mono
DEFAULT_TTS_FORMAT: Final[str] = "pcm_s16le"
DEFAULT_TTS_SAMPLE_RATE: Final[int] = 24000


@dataclass(slots=True)
class DoubaoCredentials:
    app_id: str
    access_token: str
    secret_key: str = ""
    resource_id: str = DEFAULT_RESOURCE_ID
    app_key: str = DEFAULT_APP_KEY

    def headers(self, connect_id: str | None = None) -> dict[str, str]:
        headers = {
            "X-Api-App-ID": self.app_id,
            "X-Api-Access-Key": self.access_token,
            "X-Api-Resource-Id": self.resource_id,
            "X-Api-App-Key": self.app_key,
        }
        if self.secret_key:
            # Not all Doubao routes require it, but we pass it when provided.
            headers["X-Api-Secret-Key"] = self.secret_key
        if connect_id:
            headers["X-Api-Connect-Id"] = connect_id
        return headers


@dataclass(slots=True)
class DoubaoSessionConfig:
    """Runtime-configurable Doubao session settings.

    Only the most common knobs are surfaced here; the rest can be overridden by
    passing a raw dict as `extra_start_session_payload`.
    """

    speaker: str = "zh_female_vv_jupiter_bigtts"
    model: str = "1.2.1.1"
    system_role: str | None = None
    input_mod: str = "push_to_talk"
    # Server TTS format
    tts_format: str = DEFAULT_TTS_FORMAT
    tts_sample_rate: int = DEFAULT_TTS_SAMPLE_RATE
    # Optional extras (merged on top of the default StartSession body)
    extra_start_session_payload: dict = field(default_factory=dict)


class DoubaoClientError(RuntimeError):
    """Raised for unrecoverable Doubao client errors (bad config, handshake fail)."""


class DoubaoClient:
    """One WebSocket connection to Doubao, scoped to one Miro realtime session."""

    def __init__(
        self,
        *,
        credentials: DoubaoCredentials,
        ws_url: str = DEFAULT_WS_URL,
        connect_id: str | None = None,
    ) -> None:
        self._creds = credentials
        self._ws_url = ws_url
        self._connect_id = connect_id or str(uuid.uuid4())
        self._ws: WebSocketClientProtocol | None = None
        self._session_id: str | None = None
        self._closed = False

    # ------------------------------------------------------------------ #
    # Lifecycle
    # ------------------------------------------------------------------ #

    async def connect(self) -> None:
        if websockets is None:
            raise DoubaoClientError(
                "The 'websockets' package is not installed in the backend environment."
            )
        if not self._creds.app_id or not self._creds.access_token:
            raise DoubaoClientError(
                "Doubao credentials are not configured (DOUBAO_APP_ID / DOUBAO_ACCESS_TOKEN)."
            )

        headers = self._creds.headers(connect_id=self._connect_id)
        logger.info(
            "doubao.connect url=%s connect_id=%s",
            self._ws_url,
            self._connect_id,
        )
        # `websockets` uses `additional_headers` in >=12, `extra_headers` in <12.
        try:
            self._ws = await websockets.connect(  # type: ignore[attr-defined]
                self._ws_url,
                additional_headers=headers,
                max_size=None,
                open_timeout=10,
                ping_interval=20,
                ping_timeout=20,
            )
        except TypeError:
            self._ws = await websockets.connect(  # type: ignore[attr-defined]
                self._ws_url,
                extra_headers=headers,
                max_size=None,
                open_timeout=10,
                ping_interval=20,
                ping_timeout=20,
            )

    async def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        try:
            if self._ws is not None and self._session_id is not None:
                await self._safe_send(
                    build_json_client_frame(
                        int(ClientEvent.FINISH_SESSION),
                        b"{}",
                        session_id=self._session_id,
                    )
                )
                await self._safe_send(
                    build_json_client_frame(int(ClientEvent.FINISH_CONNECTION), b"{}")
                )
        finally:
            if self._ws is not None:
                try:
                    await self._ws.close()
                except Exception:  # noqa: BLE001
                    pass
            self._ws = None

    async def __aenter__(self) -> "DoubaoClient":
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:  # noqa: ANN001
        await self.close()

    # ------------------------------------------------------------------ #
    # Control frames
    # ------------------------------------------------------------------ #

    async def start_connection(self) -> None:
        await self._require_ws().send(
            build_json_client_frame(int(ClientEvent.START_CONNECTION), b"{}")
        )

    async def start_session(
        self,
        *,
        session_id: str | None = None,
        config: DoubaoSessionConfig | None = None,
    ) -> str:
        cfg = config or DoubaoSessionConfig()
        sid = session_id or str(uuid.uuid4())
        self._session_id = sid

        payload: dict = {
            "dialog": {
                "bot_name": "Miro Coach",
                "extra": {
                    "model": cfg.model,
                },
            },
            "tts": {
                "audio_config": {
                    "format": cfg.tts_format,
                    "sample_rate": cfg.tts_sample_rate,
                    "channel": 1,
                },
                "speaker": cfg.speaker,
            },
            "asr": {
                "extra": {
                    "end_smooth_window_ms": 800,
                },
            },
            "input_audio": {
                "format": "pcm_s16le",
                "sample_rate": DEFAULT_INPUT_SAMPLE_RATE,
                "channel": DEFAULT_INPUT_CHANNELS,
                "bits": DEFAULT_INPUT_BITS,
            },
            "input_mod": cfg.input_mod,
        }
        if cfg.system_role:
            payload.setdefault("dialog", {})["system_role"] = cfg.system_role
        if cfg.extra_start_session_payload:
            payload = _deep_merge(payload, cfg.extra_start_session_payload)

        logger.info(
            "doubao.start_session session=%s speaker=%s model=%s input_mod=%s",
            sid,
            cfg.speaker,
            cfg.model,
            cfg.input_mod,
        )

        await self._require_ws().send(
            build_json_client_frame(
                int(ClientEvent.START_SESSION),
                json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                session_id=sid,
            )
        )
        return sid

    async def send_audio_chunk(self, pcm_bytes: bytes) -> None:
        if not self._session_id:
            raise DoubaoClientError("Cannot send audio before start_session().")
        await self._require_ws().send(
            build_audio_client_frame(pcm_bytes, session_id=self._session_id)
        )

    async def end_asr(self) -> None:
        if self._ws is None or self._session_id is None:
            return
        await self._safe_send(
            build_json_client_frame(
                int(ClientEvent.END_ASR),
                b"{}",
                session_id=self._session_id,
            )
        )

    async def finish_session(self) -> None:
        if self._ws is None or self._session_id is None:
            return
        await self._safe_send(
            build_json_client_frame(
                int(ClientEvent.FINISH_SESSION),
                b"{}",
                session_id=self._session_id,
            )
        )

    async def send_client_interrupt(self) -> None:
        if self._ws is None or self._session_id is None:
            return
        await self._safe_send(
            build_json_client_frame(
                int(ClientEvent.CLIENT_INTERRUPT),
                b"{}",
                session_id=self._session_id,
            )
        )

    async def say_hello(self, text: str) -> None:
        if self._ws is None or self._session_id is None:
            return
        await self._safe_send(
            build_json_client_frame(
                int(ClientEvent.SAY_HELLO),
                json.dumps({"content": text}, ensure_ascii=False).encode("utf-8"),
                session_id=self._session_id,
            )
        )

    # ------------------------------------------------------------------ #
    # Receive loop
    # ------------------------------------------------------------------ #

    async def frames(self) -> AsyncIterator[DoubaoFrame]:
        """Yield decoded Doubao frames until the connection is closed."""

        ws = self._require_ws()
        try:
            async for message in ws:
                if isinstance(message, str):
                    logger.debug("doubao.text_message message=%s", message[:200])
                    continue
                if not isinstance(message, (bytes, bytearray)):
                    continue
                try:
                    frame = decode_frame(bytes(message))
                except ValueError as exc:
                    logger.warning("doubao.decode_failed error=%s", exc)
                    continue
                yield frame
        except ConnectionClosed as exc:
            logger.info("doubao.ws_closed code=%s reason=%s", exc.code, exc.reason)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001
            logger.exception("doubao.receive_failed error=%s", exc)

    # ------------------------------------------------------------------ #
    # Internals
    # ------------------------------------------------------------------ #

    def _require_ws(self) -> WebSocketClientProtocol:
        if self._ws is None:
            raise DoubaoClientError("Doubao WebSocket is not connected.")
        return self._ws

    async def _safe_send(self, frame: bytes) -> None:
        if self._ws is None:
            return
        try:
            await self._ws.send(frame)
        except Exception as exc:  # noqa: BLE001
            logger.warning("doubao.send_failed error=%s", exc)


def _deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge `override` into `base`, returning a new dict."""

    out = dict(base)
    for key, value in override.items():
        if key in out and isinstance(out[key], dict) and isinstance(value, dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = value
    return out
