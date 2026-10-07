from app.database.url import sqlalchemy_database_url


def test_postgres_url_uses_installed_psycopg_driver():
    url = sqlalchemy_database_url(
        "postgresql://user:secret@db.example.test:6543/workbit?sslmode=require"
    )

    assert url.drivername == "postgresql+psycopg"
    assert url.host == "db.example.test"
    assert url.port == 6543
    assert url.database == "workbit"
    assert url.password == "secret"
    assert url.query["sslmode"] == "require"


def test_supabase_pooler_marker_is_not_sent_as_a_driver_option():
    url = sqlalchemy_database_url(
        "postgresql://user:secret@db.example.test:6543/workbit?pgbouncer=true&sslmode=require"
    )

    assert url.drivername == "postgresql+psycopg"
    assert "pgbouncer" not in url.query
    assert url.query["sslmode"] == "require"


def test_existing_psycopg_url_and_sqlite_url_are_preserved():
    postgres_url = sqlalchemy_database_url(
        "postgresql+psycopg://user:secret@db.example.test/workbit"
    )
    sqlite_url = sqlalchemy_database_url("sqlite:///./test-workbit.db")

    assert postgres_url.drivername == "postgresql+psycopg"
    assert sqlite_url.drivername == "sqlite"
