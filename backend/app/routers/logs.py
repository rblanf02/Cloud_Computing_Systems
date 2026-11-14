import csv
import json
from io import StringIO

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import require_permission
from ..models import LogEvent, User

router = APIRouter(prefix="/logs", tags=["logs"])

FIELDS = ["timestamp", "username", "action", "resource", "result", "details"]


def _visible_logs(db: Session, current_user: User):
    query = db.query(LogEvent)
    if not current_user.is_admin:
        query = query.filter(LogEvent.username == current_user.username)
    return query.order_by(LogEvent.timestamp.desc())


def _serialize(log: LogEvent) -> dict:
    return {
        "id": log.id,
        "timestamp": log.timestamp.isoformat(),
        "username": log.username,
        "action": log.action,
        "resource": log.resource,
        "result": log.result,
        "details": log.details,
    }


@router.get("")
def get_logs(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("read")),
):
    logs = _visible_logs(db, current_user).limit(200).all()
    return [_serialize(log) for log in logs]


@router.get("/export")
def export_logs(
    fmt: str = "json",
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("read")),
):
    if fmt not in {"json", "csv"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Formato no soportado. Usa 'json' o 'csv'",
        )

    logs = _visible_logs(db, current_user).all()
    rows = [_serialize(log) for log in logs]

    if fmt == "json":
        content = json.dumps(rows, ensure_ascii=False, indent=2)
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
