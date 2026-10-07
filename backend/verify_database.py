from __future__ import annotations

from urllib.parse import quote, quote_plus

from sqlalchemy import inspect, text
from sqlalchemy.engine import make_url

from app.core.config import settings
from app.database.session import engine

REQUIRED_TABLES = (
    "users",
    "wallets",
    "wallet_transactions",
    "offers",
    "offer_clicks",
    "offer_conversions",
    "reward_policies",
    "reward_decisions",
)


def sanitized_error(error: Exception) -> str:
    message = str(error)
    for raw_url in (settings.database_url, settings.direct_url):
        if not raw_url:
            continue
        url = make_url(raw_url)
        replacements = [raw_url, url.render_as_string(hide_password=True)]
        if url.password:
            replacements.extend(
                (url.password, quote(url.password, safe=""), quote_plus(url.password))
            )
        for secret in sorted(set(replacements), key=len, reverse=True):
            if secret:
                message = message.replace(secret, "[REDACTED]")
    return message


def main() -> int:
    url = engine.url
    print(
        "Configured application database: "
        f"host={url.host}, port={url.port}, database={url.database}, user={url.username}"
    )
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1")).scalar_one()
            print("Database connection: SUCCESS")
            print(f"SELECT 1: {'SUCCESS' if result == 1 else 'FAILED'}")
            database, user = connection.execute(
                text("SELECT current_database(), current_user")
            ).one()
            print(f"PostgreSQL identity: database={database}, user={user}")

            existing = set(inspect(connection).get_table_names(schema="public"))
            print("Required WorkBit tables:")
            for table in REQUIRED_TABLES:
                status = "PRESENT" if table in existing else "MISSING"
                print(f"{table}: {status}")
            if result != 1 or any(table not in existing for table in REQUIRED_TABLES):
                return 1
    except Exception as error:
        print("Database connection: FAILED")
        print("SELECT 1: FAILED")
        print(f"Error type: {type(error).__name__}")
        print(f"Sanitized error: {sanitized_error(error)}")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
