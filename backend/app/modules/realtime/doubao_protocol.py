"""Binary frame codec for the Doubao (Volcengine) Realtime Dialogue API.

Reference: wss://openspeech.bytedance.com/api/v3/realtime/dialogue

Frame layout (per Doubao realtime spec):

    byte 0:  [4 bits protocol_version=0b0001][4 bits header_size_in_uint32s=0b0001]
    byte 1:  [4 bits message_type][4 bits message_type_specific_flags]
    byte 2:  [4 bits serialization][4 bits compression]
    byte 3:  [4 bits reserved][4 bits reserved]

    (optional) event_id: 4 bytes big-endian int32  (present when flags & 0b0100)
    (optional) session_id: 4-byte big-endian size + utf-8 bytes
               (present for session-scoped events: 100/102/200/300/500/515)
    (optional) connect_id: 4-byte big-endian size + utf-8 bytes
               (present when the frame carries a connect id, typically server-side)
    payload: 4-byte big-endian uint32 size + bytes

This module is transport-agnostic: it only handles encode/decode of one frame's
bytes. The WebSocket client in `doubao_client.py` composes these frames.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Final

# ---------------------------------------------------------------------------
# Header constants
# ---------------------------------------------------------------------------

PROTOCOL_VERSION: Final[int] = 0b0001
HEADER_SIZE_UNITS: Final[int] = 0b0001  # 1 * 4 bytes = 4 bytes

# Message types (byte 1 high nibble)
MSG_TYPE_FULL_CLIENT_REQUEST: Final[int] = 0b0001
MSG_TYPE_AUDIO_ONLY_CLIENT: Final[int] = 0b0010
MSG_TYPE_FULL_SERVER_RESPONSE: Final[int] = 0b1001
MSG_TYPE_AUDIO_ONLY_SERVER: Final[int] = 0b1011
MSG_TYPE_ERROR: Final[int] = 0b1111

# Message flags (byte 1 low nibble, bit field)
FLAG_NONE: Final[int] = 0b0000
FLAG_HAS_EVENT: Final[int] = 0b0100

# Serialization (byte 2 high nibble)
SER_NONE: Final[int] = 0b0000
SER_JSON: Final[int] = 0b0001
SER_RAW: Final[int] = 0b1111

# Compression (byte 2 low nibble) — we always request/emit no compression here.
COMP_NONE: Final[int] = 0b0000


# ---------------------------------------------------------------------------
# Event IDs (per Doubao realtime dialogue spec)
# ---------------------------------------------------------------------------


class ClientEvent(IntEnum):
    """Events this client can send to Doubao."""

    START_CONNECTION = 1
    FINISH_CONNECTION = 2
    START_SESSION = 100
    FINISH_SESSION = 102
    TASK_REQUEST = 200  # audio upload
    END_ASR = 400
    SAY_HELLO = 300
    CHAT_TTS_TEXT = 500
    CLIENT_INTERRUPT = 515


class ServerEvent(IntEnum):
    """Events this client expects to receive from Doubao."""

    CONNECTION_STARTED = 50
    CONNECTION_FAILED = 51
    CONNECTION_FINISHED = 52
    SESSION_STARTED = 150
    SESSION_FAILED = 151
    SESSION_FINISHED = 152
    TTS_SENTENCE_START = 350
    TTS_SENTENCE_END = 351
    TTS_RESPONSE = 352
    TTS_ENDED = 359
    ASR_INFO = 450
    ASR_RESPONSE = 451
    ASR_ENDED = 459
    CHAT_RESPONSE = 550
    CHAT_ENDED = 559
    DIALOG_COMMON_ERROR = 599


# Events that carry a session_id field in their frame body.
SESSION_SCOPED_EVENTS: Final[frozenset[int]] = frozenset(
    {
        ClientEvent.START_SESSION,
        ClientEvent.FINISH_SESSION,
        ClientEvent.TASK_REQUEST,
        ClientEvent.END_ASR,
        ClientEvent.SAY_HELLO,
        ClientEvent.CHAT_TTS_TEXT,
        ClientEvent.CLIENT_INTERRUPT,
        ServerEvent.SESSION_STARTED,
        ServerEvent.SESSION_FAILED,
        ServerEvent.SESSION_FINISHED,
        ServerEvent.TTS_SENTENCE_START,
        ServerEvent.TTS_SENTENCE_END,
        ServerEvent.TTS_RESPONSE,
        ServerEvent.TTS_ENDED,
        ServerEvent.ASR_INFO,
        ServerEvent.ASR_RESPONSE,
        ServerEvent.ASR_ENDED,
        ServerEvent.CHAT_RESPONSE,
        ServerEvent.CHAT_ENDED,
    }
)


# ---------------------------------------------------------------------------
# Encode / decode
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class DoubaoFrame:
    """Decoded representation of a Doubao binary frame."""

    message_type: int
    message_flags: int
    serialization: int
    compression: int
    event_id: int | None = None
    session_id: str | None = None
    connect_id: str | None = None
    payload: bytes = b""
    extras: dict[str, object] = field(default_factory=dict)

    @property
    def is_json(self) -> bool:
        return self.serialization == SER_JSON

    @property
    def is_audio(self) -> bool:
        return self.message_type in (MSG_TYPE_AUDIO_ONLY_CLIENT, MSG_TYPE_AUDIO_ONLY_SERVER)

    @property
    def is_error(self) -> bool:
        return self.message_type == MSG_TYPE_ERROR


def encode_frame(
    *,
    message_type: int,
    event_id: int | None,
    payload: bytes,
    session_id: str | None = None,
    serialization: int = SER_JSON,
    compression: int = COMP_NONE,
    message_flags: int | None = None,
) -> bytes:
    """Encode one Doubao wire frame.

    `payload` must be the fully-serialized payload bytes (e.g. `json.dumps(...).encode()`
    for JSON events, or raw PCM bytes for audio events).
    """

    if message_flags is None:
        message_flags = FLAG_HAS_EVENT if event_id is not None else FLAG_NONE

    header = bytes(
        [
            (PROTOCOL_VERSION << 4) | HEADER_SIZE_UNITS,
            ((message_type & 0x0F) << 4) | (message_flags & 0x0F),
            ((serialization & 0x0F) << 4) | (compression & 0x0F),
            0x00,
        ]
    )

    parts: list[bytes] = [header]

    if event_id is not None:
        parts.append(struct.pack(">i", int(event_id)))

    if session_id is not None:
        sid_bytes = session_id.encode("utf-8")
        parts.append(struct.pack(">I", len(sid_bytes)))
        parts.append(sid_bytes)

    if payload is None:
        payload = b""
    parts.append(struct.pack(">I", len(payload)))
    parts.append(payload)

    return b"".join(parts)


def decode_frame(raw: bytes) -> DoubaoFrame:
    """Decode one Doubao wire frame.

    Raises ValueError on malformed frames. The caller is responsible for the
    top-level JSON payload parsing; we return raw bytes.
    """

    if len(raw) < 4:
        raise ValueError(f"Doubao frame too short: {len(raw)} bytes")

    header_byte_0 = raw[0]
    header_byte_1 = raw[1]
    header_byte_2 = raw[2]
    # byte 3 reserved

    header_size_units = header_byte_0 & 0x0F
    header_size = header_size_units * 4
    if header_size < 4:
        raise ValueError(f"Invalid header size: {header_size}")

    message_type = (header_byte_1 >> 4) & 0x0F
    message_flags = header_byte_1 & 0x0F
    serialization = (header_byte_2 >> 4) & 0x0F
    compression = header_byte_2 & 0x0F

    cursor = header_size

    event_id: int | None = None
    if message_flags & FLAG_HAS_EVENT:
        if cursor + 4 > len(raw):
            raise ValueError("Frame truncated at event_id")
        event_id = struct.unpack(">i", raw[cursor : cursor + 4])[0]
        cursor += 4

    session_id: str | None = None
    connect_id: str | None = None

    # Session id presence depends on event type.
    if event_id is not None and event_id in SESSION_SCOPED_EVENTS:
        if cursor + 4 > len(raw):
            raise ValueError("Frame truncated at session_id size")
        sid_size = struct.unpack(">I", raw[cursor : cursor + 4])[0]
        cursor += 4
        if cursor + sid_size > len(raw):
            raise ValueError("Frame truncated at session_id bytes")
        session_id = raw[cursor : cursor + sid_size].decode("utf-8", errors="replace")
        cursor += sid_size

    # Error frames from the server sometimes carry an error code before payload size.
    error_code: int | None = None
    if message_type == MSG_TYPE_ERROR:
        if cursor + 4 > len(raw):
            raise ValueError("Error frame truncated at error_code")
        error_code = struct.unpack(">i", raw[cursor : cursor + 4])[0]
        cursor += 4

    # Payload
    if cursor + 4 > len(raw):
        raise ValueError("Frame truncated at payload size")
    payload_size = struct.unpack(">I", raw[cursor : cursor + 4])[0]
    cursor += 4

    if cursor + payload_size > len(raw):
        raise ValueError(
            f"Frame truncated at payload: need {payload_size} bytes, have {len(raw) - cursor}"
        )
    payload = raw[cursor : cursor + payload_size]

    extras: dict[str, object] = {}
    if error_code is not None:
        extras["error_code"] = error_code

    return DoubaoFrame(
        message_type=message_type,
        message_flags=message_flags,
        serialization=serialization,
        compression=compression,
        event_id=event_id,
        session_id=session_id,
        connect_id=connect_id,
        payload=payload,
        extras=extras,
    )


# ---------------------------------------------------------------------------
# High-level frame builders
# ---------------------------------------------------------------------------


def build_json_client_frame(
    event_id: int,
    payload_json_bytes: bytes,
    *,
    session_id: str | None = None,
) -> bytes:
    """Build a JSON-serialized client control frame (StartConnection, StartSession, etc.)."""

    return encode_frame(
        message_type=MSG_TYPE_FULL_CLIENT_REQUEST,
        event_id=event_id,
        payload=payload_json_bytes,
        session_id=session_id,
        serialization=SER_JSON,
        compression=COMP_NONE,
    )


def build_audio_client_frame(
    audio_bytes: bytes,
    *,
    session_id: str,
    event_id: int = int(ClientEvent.TASK_REQUEST),
) -> bytes:
    """Build a TaskRequest audio frame (raw PCM or Opus payload)."""

    return encode_frame(
        message_type=MSG_TYPE_AUDIO_ONLY_CLIENT,
        event_id=event_id,
        payload=audio_bytes,
        session_id=session_id,
        serialization=SER_RAW,
        compression=COMP_NONE,
    )
