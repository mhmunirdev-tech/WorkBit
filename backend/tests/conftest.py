import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.environ["DATABASE_URL"] = "sqlite:///./test-workbit.db"
from app.database.base import Base
from app.database.session import get_db
from app.main import app
from app.services import auth as auth_service
from app.services.seed import seed

engine = create_engine("sqlite:///./test-workbit.db", connect_args={"check_same_thread": False})
TestingSession = sessionmaker(bind=engine, autocommit=False, autoflush=False)

@pytest.fixture(autouse=True)
def database(monkeypatch):
    monkeypatch.setattr(auth_service.email_service, "send_verification", lambda recipient, token: None)
    monkeypatch.setattr(auth_service.email_service, "send_password_reset", lambda recipient, token: None)
    Base.metadata.drop_all(engine); Base.metadata.create_all(engine)
    def override():
        db = TestingSession()
        try: yield db
        finally: db.close()
    app.dependency_overrides[get_db] = override
    import app.services.seed as seed_module
    old = seed_module.SessionLocal; seed_module.SessionLocal = TestingSession
    seed(); seed_module.SessionLocal = old
    yield
    app.dependency_overrides.clear(); Base.metadata.drop_all(engine)

@pytest.fixture
def client():
    with TestClient(app) as client:
        yield client
