import csv
import json
from io import StringIO

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import LogEvent, User
from ..schemas import LogEventOut

router = APIRouter(prefix="/logs", tags=["logs"])

FIELDS = ["log_id", "created_at", "username", "action", "status", "ip_address"]


def _visible_logs(db: Session, current_user: User):
    query = db.query(LogEvent)
    if not current_user.is_admin:
        query = query.filter(LogEvent.user_id == current_user.user_id)
    return query.order_by(LogEvent.created_at.desc())


def _serialize(db: Session, log: LogEvent) -> dict:
    username = None
    if log.user_id is not None:
        user = db.query(User).filter(User.user_id == log.user_id).first()
        username = user.username if user else None
    return {
        "log_id": log.log_id,
        "user_id": log.user_id,
        "username": username,
        "file_id": log.file_id,
        "action": log.action,
        "status": log.status,
        "ip_address": log.ip_address,
        "created_at": log.created_at,
    }


@router.get("", response_model=list[LogEventOut])
def get_logs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    logs = _visible_logs(db, current_user).limit(100).all()
    return [_serialize(db, log) for log in logs]


@router.get("/export")
def export_logs(
    fmt: str = "json",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if fmt not in {"json", "csv"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Formato no soportado. Usa 'json' o 'csv'",
        )

    logs = _visible_logs(db, current_user).all()
    rows = [_serialize(db, log) for log in logs]

    if fmt == "json":
        content = json.dumps(rows, ensure_ascii=False, indent=2, default=str)
        media_type = "application/json"
    else:
        buffer = StringIO()
        writer = csv.DictWriter(buffer, fieldnames=FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
        content = buffer.getvalue()
        media_type = "text/csv"

    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="logbook.{fmt}"'},
    )
