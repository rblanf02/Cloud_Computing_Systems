from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import require_admin
from ..logbook import write_log
from ..models import File as FileModel
from ..models import User
from ..schemas import FileOut, UserOut
from .files import _file_out

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users", response_model=list[UserOut])
def list_users(
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin),
):
    users = db.query(User).order_by(User.username).all()
    result = [UserOut.model_validate(user) for user in users]

    write_log(db, action="ADMIN_LIST_USERS", user_id=current_admin.user_id, status="OK")
    db.commit()
    return result


@router.get("/files", response_model=list[FileOut])
def list_all_files(
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin),
):
    files = db.query(FileModel).order_by(FileModel.owner_id, FileModel.file_id.desc()).all()
    result = [_file_out(db, file) for file in files]

    write_log(db, action="ADMIN_LIST_FILES", user_id=current_admin.user_id, status="OK")
    db.commit()
    return result
