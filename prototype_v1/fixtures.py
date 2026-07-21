import json
from pathlib import Path
from typing import Any


def load_fixture(path: Path, *, app_env: str) -> dict[str, Any]:
    if app_env != "test":
        raise ValueError("fixtures require APP_ENV=test")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("fixture") is not True:
        raise ValueError("fixture=true marker is required")
    return payload
