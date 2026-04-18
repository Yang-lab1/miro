from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from app.modules.realtime.healthcheck import (
    DEFAULT_AUDIO_FIXTURE,
    run_synthetic_realtime_voice_healthcheck,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the backend realtime voice synthetic health check.")
    parser.add_argument("--user-email", default=None, help="Optional actor email to own the synthetic session.")
    parser.add_argument("--country-key", default="Japan", help="Country key to seed the synthetic simulation.")
    parser.add_argument(
        "--audio-fixture",
        default=str(DEFAULT_AUDIO_FIXTURE),
        help="Path to a mono PCM16 16kHz WAV fixture.",
    )
    parser.add_argument("--timeout-seconds", type=float, default=20.0)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = asyncio.run(
        run_synthetic_realtime_voice_healthcheck(
            user_email=args.user_email,
            country_key=args.country_key,
            audio_fixture_path=Path(args.audio_fixture),
            timeout_seconds=args.timeout_seconds,
        )
    )
    print(
        json.dumps(
            {
                "realtime_session_id": result.realtime_session_id,
                "observability": result.report,
                "db_session": result.db_session,
                "db_turns": result.db_turns,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
