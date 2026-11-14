from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.database.url import sqlalchemy_connect_args, sqlalchemy_database_url

database_url = sqlalchemy_database_url(settings.database_url)
engine = create_engine(
    database_url,
    pool_pre_ping=True,
    connect_args=sqlalchemy_connect_args(database_url),
)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
