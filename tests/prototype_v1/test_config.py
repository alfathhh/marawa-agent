import pytest

from prototype_v1.config import load_config


def test_rejects_non_loopback_allowed_origin(monkeypatch):
    monkeypatch.setenv("ALLOWED_ORIGIN", "https://public.example")

    with pytest.raises(ValueError, match="ALLOWED_ORIGIN"):
        load_config()


def test_rejects_invalid_environment(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")

    with pytest.raises(ValueError, match="APP_ENV"):
        load_config()


def test_defaults_to_development_loopback_config(monkeypatch):
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("ALLOWED_ORIGIN", raising=False)

    config = load_config()

    assert config.app_env == "development"
    assert config.allowed_origin == "http://127.0.0.1:8010"
