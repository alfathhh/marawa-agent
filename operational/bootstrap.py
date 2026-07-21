import os

from sqlalchemy import create_engine, text

from operational.dashboard_security import hash_password


def main():
    database_url = os.environ["DATABASE_URL"]
    username = os.getenv("BOOTSTRAP_ADMIN_USERNAME", "admin")
    password = os.environ["BOOTSTRAP_ADMIN_PASSWORD"]
    engine = create_engine(database_url, pool_pre_ping=True)
    with engine.begin() as connection:
        exists = connection.execute(
            text(
                "SELECT 1 FROM dashboard_users WHERE role='superadmin' AND active LIMIT 1"
            )
        ).scalar_one_or_none()
        if not exists:
            connection.execute(
                text("""
                    INSERT INTO dashboard_users
                        (username, password_hash, role, must_change_password)
                    VALUES (:username, :password_hash, 'superadmin', true)
                """),
                {"username": username, "password_hash": hash_password(password)},
            )
    engine.dispose()


if __name__ == "__main__":
    main()
