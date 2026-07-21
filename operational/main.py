import os

from operational.app import create_app


def from_env():
    required = {
        "DATABASE_URL": os.getenv("DATABASE_URL"),
        "EVOLUTION_API_URL": os.getenv("EVOLUTION_API_URL"),
        "EVOLUTION_API_KEY": os.getenv("EVOLUTION_API_KEY"),
        "EVOLUTION_INSTANCE": os.getenv("EVOLUTION_INSTANCE"),
        "WEBHOOK_SECRET": os.getenv("WEBHOOK_SECRET"),
        "DASHBOARD_SESSION_SECRET": os.getenv("DASHBOARD_SESSION_SECRET"),
        "DASHBOARD_ORIGIN": os.getenv("DASHBOARD_ORIGIN"),
    }
    missing = [key for key, value in required.items() if not value]
    if missing:
        raise RuntimeError("Missing operational configuration: " + ", ".join(missing))
    return create_app(
        database_url=required["DATABASE_URL"],
        evolution_url=required["EVOLUTION_API_URL"],
        evolution_key=required["EVOLUTION_API_KEY"],
        evolution_instance=required["EVOLUTION_INSTANCE"],
        webhook_secret=required["WEBHOOK_SECRET"],
        session_secret=required["DASHBOARD_SESSION_SECRET"],
        allowed_origin=required["DASHBOARD_ORIGIN"],
        production=os.getenv("APP_ENV") == "production",
    )


app = from_env()
