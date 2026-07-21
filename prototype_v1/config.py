from dataclasses import dataclass
import os
from urllib.parse import urlparse


LOOPBACK_ORIGIN = "http://127.0.0.1:8010"


def _validate_loopback_origin(origin: str) -> str:
    parsed = urlparse(origin)
    if (
        parsed.scheme not in {"http", "https"}
        or parsed.hostname not in {"127.0.0.1", "localhost"}
        or parsed.path
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("ALLOWED_ORIGIN must be a loopback origin")
    return origin


@dataclass(frozen=True)
class Config:
    app_env: str
    allowed_origin: str


def load_config() -> Config:
    app_env = os.getenv("APP_ENV", "development")
    if app_env not in {"development", "test"}:
        raise ValueError("APP_ENV must be development or test")
    return Config(
        app_env=app_env,
        allowed_origin=_validate_loopback_origin(
            os.getenv("ALLOWED_ORIGIN", LOOPBACK_ORIGIN)
        ),
    )
