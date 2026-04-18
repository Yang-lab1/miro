from __future__ import annotations

import json
import math
import os
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np


ROOT = Path(r"C:\Users\Yang\Desktop\miro")
TMP = ROOT / "tmp"
BACKEND_PY = ROOT / "backend" / ".venv" / "Scripts" / "python.exe"
HEALTHCHECK = ROOT / "backend" / "scripts" / "run_realtime_voice_healthcheck.py"
SUCCESS_FIXTURE = ROOT / "backend" / "scripts" / "fixtures" / "hello_can_you_hear_me.wav"
FILES = {
    "synthetic_success": SUCCESS_FIXTURE,
    "browser_mix_48k": TMP / "browser_capture_hello_trimmed_48k.wav",
    "browser_left_48k": TMP / "browser_capture_left_trimmed_48k.wav",
    "browser_right_48k": TMP / "browser_capture_right_trimmed_48k.wav",
    "browser_ws_16k": TMP / "browser_ws_sent_hello_trimmed.wav",
}


def read_wav(path: Path) -> tuple[np.ndarray, int, int]:
    with wave.open(str(path), "rb") as wf:
        channels = wf.getnchannels()
        sample_rate = wf.getframerate()
        sample_width = wf.getsampwidth()
        frames = wf.readframes(wf.getnframes())
    if sample_width != 2:
        raise ValueError(f"{path} sample width {sample_width} unsupported")
    data = np.frombuffer(frames, dtype="<i2").astype(np.int16)
    if channels > 1:
        data = data.reshape(-1, channels)
    return data, sample_rate, channels


def write_wav(path: Path, data: np.ndarray, sample_rate: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pcm = np.asarray(data, dtype=np.int16)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm.astype("<i2").tobytes())


def mono_float(data: np.ndarray) -> np.ndarray:
    if data.ndim == 2:
        mono = data.mean(axis=1)
    else:
        mono = data.astype(np.float64)
    return mono.astype(np.float64) / 32768.0


def band_share(x: np.ndarray, sample_rate: int, lo: float, hi: float) -> float:
    if not len(x):
        return 0.0
    nfft = 1 << (len(x) - 1).bit_length()
    spectrum = np.fft.rfft(x, n=nfft)
    freqs = np.fft.rfftfreq(nfft, d=1.0 / sample_rate)
    power = np.abs(spectrum) ** 2
    total = float(power.sum()) or 1.0
    mask = (freqs >= lo) & (freqs < hi)
    return float(power[mask].sum() / total)


def summarize(path: Path) -> dict:
    data, sample_rate, channels = read_wav(path)
    x = mono_float(data)
    absx = np.abs(x)
    rms = float(np.sqrt(np.mean(np.square(x)))) if len(x) else 0.0
    peak = float(absx.max()) if len(x) else 0.0
    min_v = float(x.min()) if len(x) else 0.0
    max_v = float(x.max()) if len(x) else 0.0
    zero_ratio = float(np.mean(x == 0)) if len(x) else 1.0
    near_zero_ratio = float(np.mean(absx < 1e-4)) if len(x) else 1.0
    clipped_ratio = float(np.mean(absx >= 0.999)) if len(x) else 0.0
    threshold = max(0.01, rms * 0.8)
    voiced = absx >= threshold
    voiced_ratio = float(np.mean(voiced)) if len(x) else 0.0
    voiced_duration_sec = float(voiced.sum() / sample_rate) if sample_rate else 0.0
    return {
        "path": str(path),
        "sample_rate": sample_rate,
        "channel_count": channels,
        "bit_depth": 16,
        "duration_sec": len(x) / sample_rate if sample_rate else 0.0,
        "sample_count": int(len(x)),
        "byte_length": int(len(x) * 2),
        "rms": rms,
        "peak": peak,
        "min": min_v,
        "max": max_v,
        "zero_ratio": zero_ratio,
        "near_zero_ratio": near_zero_ratio,
        "clipped_ratio": clipped_ratio,
        "voiced_ratio": voiced_ratio,
        "voiced_duration_sec": voiced_duration_sec,
        "band_0_200": band_share(x, sample_rate, 0, 200),
        "band_200_3400": band_share(x, sample_rate, 200, 3400),
        "band_3400_8000": band_share(x, sample_rate, 3400, 8000),
        "band_8000_plus": band_share(x, sample_rate, 8000, sample_rate / 2),
    }


def lowpass_decimate_to_16k(data: np.ndarray, sample_rate: int, cutoff_hz: float = 3600.0) -> np.ndarray:
    x = mono_float(data)
    if sample_rate == 16000:
        return np.clip(np.round(x * 32767.0), -32768, 32767).astype(np.int16)
    if sample_rate % 16000 != 0:
        raise ValueError(f"Unsupported sample rate for exact decimation: {sample_rate}")
    factor = sample_rate // 16000
    taps = 127
    n = np.arange(taps) - (taps - 1) / 2
    fc = cutoff_hz / sample_rate
    kernel = 2 * fc * np.sinc(2 * fc * n)
    kernel *= np.hamming(taps)
    kernel /= kernel.sum()
    filtered = np.convolve(x, kernel, mode="same")
    decimated = filtered[::factor]
    return np.clip(np.round(decimated * 32767.0), -32768, 32767).astype(np.int16)


def apply_gain_to_target_rms(pcm16: np.ndarray, target_rms: float) -> np.ndarray:
    x = pcm16.astype(np.float64) / 32768.0
    current_rms = math.sqrt(float(np.mean(np.square(x)))) if len(x) else 0.0
    if current_rms <= 1e-9:
        return pcm16
    gain = target_rms / current_rms
    peak = float(np.max(np.abs(x))) if len(x) else 1.0
    if peak * gain > 0.98:
        gain = 0.98 / peak
    y = np.clip(x * gain, -1.0, 1.0)
    return np.clip(np.round(y * 32767.0), -32768, 32767).astype(np.int16)


def run_healthcheck(audio_fixture: Path) -> dict:
    proc = subprocess.run(
        [
            str(BACKEND_PY),
            str(HEALTHCHECK),
            "--audio-fixture",
            str(audio_fixture),
            "--timeout-seconds",
            "20",
        ],
        capture_output=True,
        text=True,
        check=True,
        cwd=str(ROOT / "backend"),
    )
    return json.loads(proc.stdout)


def build_channel_variants() -> dict[str, Path]:
    mix, mix_sr, _ = read_wav(FILES["browser_mix_48k"])
    left, left_sr, _ = read_wav(FILES["browser_left_48k"])
    right, right_sr, _ = read_wav(FILES["browser_right_48k"])

    mix_linear, _, _ = read_wav(TMP / "browser_capture_hello_trimmed.wav")
    ws_linear, _, _ = read_wav(FILES["browser_ws_16k"])

    target_rms = summarize(SUCCESS_FIXTURE)["rms"]

    variants = {
        "left_only_improved": lowpass_decimate_to_16k(left, left_sr),
        "right_only_improved": lowpass_decimate_to_16k(right, right_sr),
        "mix_improved": lowpass_decimate_to_16k(mix, mix_sr),
        "mix_current_linear": mono_float(mix_linear),
        "ws_current_linear": mono_float(ws_linear),
    }

    paths: dict[str, Path] = {}
    for name, pcm in variants.items():
        if pcm.dtype != np.int16:
            pcm = np.clip(np.round(pcm * 32767.0), -32768, 32767).astype(np.int16)
        out = TMP / f"{name}.wav"
        write_wav(out, pcm, 16000)
        paths[name] = out

    gained = apply_gain_to_target_rms(read_wav(paths["mix_improved"])[0], target_rms)
    gained_path = TMP / "mix_improved_gain.wav"
    write_wav(gained_path, gained, 16000)
    paths["mix_improved_gain"] = gained_path
    return paths


def main() -> None:
    analysis = {name: summarize(path) for name, path in FILES.items()}
    variant_paths = build_channel_variants()
    variant_summaries = {name: summarize(path) for name, path in variant_paths.items()}

    replay_results = {}
    for name, path in variant_paths.items():
        result = run_healthcheck(path)
        obs = result["observability"]
        replay_results[name] = {
            "fixture": str(path),
            "realtime_session_id": result["realtime_session_id"],
            "user_transcript_event_count": obs["user_transcript_event_count"],
            "assistant_text_event_count": obs["assistant_text_event_count"],
            "assistant_audio_chunk_count": obs["assistant_audio_chunk_count"],
            "assistant_turn_end_count": obs["assistant_turn_end_count"],
            "persisted_turn_count": obs["persisted_turn_count"],
            "final_status": obs["final_status"],
            "root_block_point": obs["root_block_point"],
            "last_error_code": obs["last_error_code"],
            "last_error_message": obs["last_error_message"],
        }

    out = {
        "analysis": analysis,
        "variant_summaries": variant_summaries,
        "replay_results": replay_results,
    }
    out_path = TMP / "browser_audio_experiments_result.json"
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(str(out_path))


if __name__ == "__main__":
    main()
