from sqlalchemy.orm import Session

from .models import LogEvent


def write_log(
    db: Session,
    action: str,
    *,
    user_id: int | None = None,
    file_id: int | None = None,
    status: str = "OK",
    ip_address: str | None = None,
) -> LogEvent:
    event = LogEvent(
        user_id=user_id,
        file_id=file_id,
        action=action,
        status=status,
        ip_address=ip_address,
    )
    db.add(event)
    return event
