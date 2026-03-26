import json
from functools import lru_cache
from pathlib import Path


def _shared_root() -> Path:
    return Path(__file__).resolve().parents[3] / "shared"


@lru_cache
def load_enum_keys(enum_name: str) -> set[str]:
    path = _shared_root() / "enums" / f"{enum_name}.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    values = payload.get("values", [])
    keys: set[str] = set()

    for item in values:
        if isinstance(item, str):
            keys.add(item)
        elif isinstance(item, dict) and "key" in item:
            keys.add(str(item["key"]))

    return keys
