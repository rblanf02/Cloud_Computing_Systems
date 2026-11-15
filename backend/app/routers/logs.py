from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import LogEvent, User
from ..schemas import LogEventOut

router = APIRouter(prefix="/logs", tags=["logs"])


@router.get("", response_model=list[LogEventOut])
def get_logs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(LogEvent)
    if not current_user.is_admin:
        query = query.filter(LogEvent.user_id == current_user.user_id)
    logs = query.order_by(LogEvent.created_at.desc()).limit(100).all()
    return logs