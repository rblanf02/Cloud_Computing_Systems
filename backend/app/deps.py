from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .config import settings
from .database import get_db
from .models import File, User, UserSession
from .security import decode_token

bearer_scheme = HTTPBearer(auto_error=False)


@dataclass
class AuthContext:
    user: User
    session: UserSession


def _auth_error(detail: str = "Token ausente o invalido") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_auth_context(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> AuthContext:
    if credentials is None:
        raise _auth_error()

    payload = decode_token(credentials.credentials)
    if payload is None:
        raise _auth_error()

    username = payload.get("sub")
    session_id = payload.get("sid")
    if not isinstance(username, str) or not isinstance(session_id, str):
        raise _auth_error()

    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise _auth_error()

    session = (
        db.query(UserSession)
        .filter(
            UserSession.id == session_id,
            UserSession.user_id == user.id,
        )
        .first()
    )
    if session is None or session.revoked_at is not None:
        raise _auth_error()

    now = datetime.now(timezone.utc)
    last_activity = session.last_activity_at
    if last_activity.tzinfo is None:
        last_activity = last_activity.replace(tzinfo=timezone.utc)

    if now - last_activity > timedelta(minutes=settings.session_idle_minutes):
        session.revoked_at = now
        db.commit()
        raise _auth_error("Sesion expirada por inactividad")

    session.last_activity_at = now
    db.commit()

    return AuthContext(user=user, session=session)


def get_current_user(
    context: AuthContext = Depends(get_auth_context),
) -> User:
    return context.user


def require_permission(permission: str):
    def checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.is_admin:
            return current_user
        if not getattr(current_user, f"can_{permission}", False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permiso '{permission}' requerido",
            )
        return current_user

    return checker


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requiere administrador",
        )
    return current_user


def get_owned_file(
    db: Session,
    file_id: int,
    user: User,
    *,
    for_update: bool = False,
) -> File:
    query = db.query(File).filter(File.id == file_id)
    if not user.is_admin:
        query = query.filter(File.owner_id == user.id)
    if for_update:
        query = query.with_for_update()

    file = query.first()
    if file is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fichero no encontrado",
        )
    return file
