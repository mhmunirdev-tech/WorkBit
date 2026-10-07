from sqlalchemy.engine import URL, make_url


def sqlalchemy_database_url(value: str) -> URL:
    url = make_url(value)
    if "pgbouncer" in url.query:
        url = url.set(query={key: val for key, val in url.query.items() if key != "pgbouncer"})
    if url.drivername in {"postgres", "postgresql"}:
        return url.set(drivername="postgresql+psycopg")
    return url
