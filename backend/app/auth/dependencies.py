from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated

from fastapi import Depends, Header
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.auth.security import hash_token
from backend.app.core.errors import AppError, ErrorCode
from backend.app.db.models import User, UserSession
from backend.app.db.session import get_db


def current_user(
    authorization: Annotated[str | None, Header()] = None,
    db: Session = Depends(get_db),
) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise AppError(ErrorCode.AUTH_REQUIRED, "authentication required", 401)
    token = authorization.removeprefix("Bearer ").strip()
    session = db.scalar(select(UserSession).where(UserSession.token_hash == hash_token(token)))
    now = datetime.now(timezone.utc)
    if session is None or session.revoked_at is not None or _as_utc(session.expires_at) <= now:
        raise AppError(ErrorCode.AUTH_INVALID, "invalid or expired session", 401)
    user = db.get(User, session.user_id)
    if user is None or not user.is_active:
        raise AppError(ErrorCode.AUTH_INVALID, "invalid or expired session", 401)
    return user


def _as_utc(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


def require_roles(*allowed: str) -> object:
    def dependency(user: User = Depends(current_user)) -> User:
        if not {role.name for role in user.roles}.intersection(allowed):
            raise AppError(ErrorCode.RBAC_DENIED, "insufficient role", 403)
        return user

    return Depends(dependency)
