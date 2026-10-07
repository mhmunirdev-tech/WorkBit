from fastapi import Cookie, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.config import settings
from app.database.session import get_db
from app.models import User
from app.security.tokens import read_session

def current_user(session: str | None = Cookie(default=None, alias=settings.session_cookie_name), db: Session = Depends(get_db)) -> User:
    user_id = read_session(session) if session else None
    user = db.get(User, user_id) if user_id else None
    if not user: raise HTTPException(401)
    return user
def require_permission(permission: str):
    def dependency(user: User = Depends(current_user)) -> User:
        permissions = {p.name for role in user.roles for p in role.permissions}
        if permission not in permissions: raise HTTPException(403)
        return user
    return dependency
