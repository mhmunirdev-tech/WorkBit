import hashlib
import secrets
from datetime import datetime, timedelta, timezone
import jwt
from app.core.config import settings

def create_session(user_id: str) -> str:
    return jwt.encode({"sub": user_id, "exp": datetime.now(timezone.utc) + timedelta(seconds=settings.session_max_age_seconds)}, settings.session_secret, algorithm="HS256")
def read_session(value: str) -> str | None:
    try: return str(jwt.decode(value, settings.session_secret, algorithms=["HS256"])["sub"])
    except jwt.PyJWTError: return None
def generate_token() -> str: return secrets.token_urlsafe(32)
def token_hash(token: str) -> str: return hashlib.sha256(token.encode()).hexdigest()
