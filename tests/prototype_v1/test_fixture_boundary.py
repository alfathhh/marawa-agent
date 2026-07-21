import json

import pytest

from prototype_v1.fixtures import load_fixture


def test_fixture_loader_rejects_non_test_environment(tmp_path):
    fixture = tmp_path / "sample.json"
    fixture.write_text(json.dumps({"fixture": True, "data": {}}))

    with pytest.raises(ValueError, match="APP_ENV=test"):
        load_fixture(fixture, app_env="development")


def test_fixture_loader_rejects_unmarked_fixture(tmp_path):
    fixture = tmp_path / "sample.json"
    fixture.write_text(json.dumps({"data": {}}))

    with pytest.raises(ValueError, match="fixture=true"):
        load_fixture(fixture, app_env="test")


def test_fixture_loader_returns_marked_fixture_in_test_environment(tmp_path):
    fixture = tmp_path / "sample.json"
    fixture.write_text(json.dumps({"fixture": True, "data": {"ok": True}}))

    payload = load_fixture(fixture, app_env="test")

    assert payload["data"] == {"ok": True}
