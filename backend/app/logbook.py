from sqlalchemy.orm import Session

from .models import LogEvent


def write_log(
    db: Session,
    action: str,
    username: str | None = None,
    resource: str | None = None,
    result: str = "OK",
    details: str | None = None,
) -> LogEvent:
    event = LogEvent(
        username=username,
        action=action,
        resource=resource,
        result=result,
        details=details,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event
