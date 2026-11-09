from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import LogEvent, User
from ..deps import require_permission

router = APIRouter(prefix="/logs", tags=["logs"])

@router.get("")
def get_logs(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("read"))
):
    logs = (
        db.query(LogEvent)
        .order_by(LogEvent.timestamp.desc())
        .limit(100)
        .all()
    )
    
    return [
        {
            "id": log.id,
            "timestamp": log.timestamp.isoformat(),
            "username": log.username,
            "action": log.action,
            "resource": log.resource,
            "result": log.result,
            "details": log.details
        }
        for log in logs
    ]