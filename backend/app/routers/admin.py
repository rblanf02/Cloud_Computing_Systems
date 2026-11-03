from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import require_admin
from ..logbook import write_log
from ..models import File as FileModel
from ..models import User
from ..schemas import FileOut, UserOut, UserPermissionsUpdate
from .files import _file_out

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users", response_model=list[UserOut])
def list_users(
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin),
):
    users = db.query(User).order_by(User.username).all()
    result = [UserOut.model_validate(user) for user in users]

    write_log(
        db,
        action="ADMIN_LIST_USERS",
        username=current_admin.username,
        resource="users",
    )
    db.commit()
    return result


@router.patch("/users/{user_id}/permissions", response_model=UserOut)
def update_user_permissions(
    user_id: int,
    payload: UserPermissionsUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin),
):
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado",
        )

    updates = payload.model_dump(exclude_unset=True, exclude_none=True)
    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se indico ningun permiso",
        )

    for field, value in updates.items():
        setattr(user, field, value)

    detail = ", ".join(f"{field}={value}" for field, value in updates.items())
    write_log(
        db,
        action="ADMIN_UPDATE_PERMISSIONS",
        username=current_admin.username,
        resource=f"user:{user.id}",
        details=detail,
    )
    db.commit()
    db.refresh(user)
    return user


@router.get("/files", response_model=list[FileOut])
def list_all_files(
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin),
):
    files = (
        db.query(FileModel)
        .order_by(FileModel.owner_id, FileModel.created_at.desc())
        .all()
    )

    result = [_file_out(db, file) for file in files]

    write_log(
        db,
        action="ADMIN_LIST_FILES",
        username=current_admin.username,
        resource="files",
    )
    db.commit()
    return result
