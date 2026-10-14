from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .database import get_db
from .models import User
from .security import decode_token

bearer_scheme = HTTPBearer(auto_error=False)


def _auth_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token ausente o invalido",
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise _auth_error()

    payload = decode_token(credentials.credentials)
    if payload is None:
        raise _auth_error()

    username = payload.get("sub")
    if username is None:
        raise _auth_error()

    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise _auth_error()

    return user


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
