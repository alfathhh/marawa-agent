from pathlib import Path

import yaml


ROOT = Path(__file__).parents[2]


def compose():
    return yaml.safe_load((ROOT / "compose.yaml").read_text())


def test_full_stack_contract():
    data = compose()
    services = data["services"]
    assert data["name"] == "marawa"
    assert set(services) == {
        "db",
        "migrate",
        "app",
        "worker",
        "evolution-db",
        "redis",
        "evolution",
    }
    assert services["db"]["image"].startswith("postgres:17")
    assert services["evolution-db"]["image"].startswith("postgres:15")
    assert services["redis"]["image"] == "redis:7-alpine"
    assert services["evolution"]["image"] == "evoapicloud/evolution-api:v2.3.7"
    assert services["app"]["ports"] == ["127.0.0.1:8020:8080"]
    assert services["evolution"]["ports"] == ["127.0.0.1:8082:8080"]
    assert (
        services["app"]["depends_on"]["migrate"]["condition"]
        == "service_completed_successfully"
    )
    assert (
        services["worker"]["depends_on"]["migrate"]["condition"]
        == "service_completed_successfully"
    )
    assert (
        services["evolution"]["environment"]["WEBHOOK_GLOBAL_URL"]
        == "http://app:8080/webhooks/evolution"
    )
    assert (
        services["evolution"]["environment"]["WEBHOOK_GLOBAL_HEADERS"]
        == '{"X-Webhook-Secret":"${WEBHOOK_SECRET:?set WEBHOOK_SECRET}"}'
    )
    assert all(
        "healthcheck" in services[name]
        for name in ("db", "app", "evolution-db", "redis", "evolution")
    )
    assert set(data["volumes"]) == {
        "marawa-db",
        "evolution-db",
        "evolution-redis",
        "evolution-instances",
    }


def test_images_and_examples_do_not_embed_secrets():
    dockerfile = (ROOT / "Dockerfile").read_text()
    example = (ROOT / ".env.example").read_text()
    assert "ENV " not in dockerfile or "PASSWORD" not in dockerfile
    for line in example.splitlines():
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            if any(word in key for word in ("PASSWORD", "SECRET", "API_KEY")):
                assert value == ""


def test_single_replica_is_explicit():
    services = compose()["services"]
    assert services["app"]["deploy"]["replicas"] == 1
    assert services["worker"]["deploy"]["replicas"] == 1
