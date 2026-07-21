import json
import os
import urllib.error
import urllib.request


BASE_URL = os.environ["EVOLUTION_API_URL"].rstrip("/")
HEADERS = {
    "apikey": os.environ["EVOLUTION_API_KEY"],
    "Content-Type": "application/json",
}
INSTANCE = os.environ["EVOLUTION_INSTANCE"]


def request(method, path, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(
        BASE_URL + path, data=data, headers=HEADERS, method=method
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return response.status, json.loads(response.read() or b"{}")
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read() or b"{}")


def main():
    status, instances = request("GET", "/instance/fetchInstances")
    if status != 200:
        raise RuntimeError("Evolution instance lookup failed")
    names = {
        item.get("name") or item.get("instance", {}).get("instanceName")
        for item in instances
        if isinstance(item, dict)
    }
    if INSTANCE not in names:
        status, _ = request(
            "POST",
            "/instance/create",
            {
                "instanceName": INSTANCE,
                "integration": "WHATSAPP-BAILEYS",
                "qrcode": True,
                "groupsIgnore": True,
                "alwaysOnline": False,
                "readMessages": False,
                "readStatus": False,
                "syncFullHistory": False,
            },
        )
        if status != 201:
            raise RuntimeError("Evolution instance creation failed")
    status, webhook = request(
        "POST",
        f"/webhook/set/{INSTANCE}",
        {
            "webhook": {
                "enabled": True,
                "url": "http://app:8080/webhooks/evolution",
                "webhookByEvents": False,
                "webhookBase64": False,
                "headers": {"X-Webhook-Secret": os.environ["WEBHOOK_SECRET"]},
                "events": [
                    "MESSAGES_UPSERT",
                    "MESSAGES_UPDATE",
                    "CONNECTION_UPDATE",
                ],
            }
        },
    )
    if (
        status not in {200, 201}
        or webhook.get("url") != "http://app:8080/webhooks/evolution"
    ):
        raise RuntimeError("Evolution webhook setup failed")


if __name__ == "__main__":
    main()
