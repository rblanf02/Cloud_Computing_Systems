from datetime import datetime, timezone
from urllib.parse import quote

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Response,
    UploadFile,
    status,
)
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..deps import get_file_with_access, get_owned_file, require_permission
from ..logbook import write_log
from ..models import File as FileModel
from ..models import FileShare, FileVersion, User
from ..schemas import FileOut, FileShareCreate, FileVersionOut
from ..storage import Storage, get_storage

router = APIRouter(prefix="/files", tags=["files"])


def _safe_filename(filename: str | None) -> str:
    name = (filename or "").replace("\\", "/").split("/")[-1]
    name = "".join(char for char in name if char.isprintable()).strip()
    if name in {"", ".", ".."}:
        return "file"
    return name[:255]


def _content_disposition(filename: str) -> str:
    fallback = filename.encode("ascii", "ignore").decode().replace('"', "_")
    fallback = fallback or "file"
    encoded = quote(filename, safe="")
    return f'attachment; filename="{fallback}"; filename*=UTF-8\'\'{encoded}'


def _delete_blob(storage: Storage, blob_name: str) -> None:
    try:
        storage.delete(blob_name)
    except Exception:
        pass


def _file_out(db: Session, file: FileModel) -> FileOut:
    version = (
        db.query(FileVersion)
        .filter(
            FileVersion.file_id == file.id,
            FileVersion.version_number == file.current_version,
        )
        .first()
    )
    return FileOut(
        id=file.id,
        owner_id=file.owner_id,
        owner_username=file.owner.username,
        filename=file.filename,
        content_type=file.content_type,
        current_version=file.current_version,
        size_bytes=version.size_bytes if version else 0,
        version_created_at=version.created_at if version else file.created_at,
        created_at=file.created_at,
    )


def _version_out(version: FileVersion) -> FileVersionOut:
    return FileVersionOut(
        id=version.id,
        version_number=version.version_number,
        size_bytes=version.size_bytes,
        content_type=version.content_type,
        created_at=version.created_at,
        created_by=version.created_by,
        created_by_username=version.created_by_user.username,
    )


def _read_upload(file: UploadFile) -> tuple[bytes, str]:
    data = file.file.read()
    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    if len(data) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum allowed limit of {settings.max_upload_size_mb} MB",
        )
    return data, file.content_type or "application/octet-stream"


def _check_user_quota(
    db: Session, user_id: int, quota_bytes: int, new_file_bytes: int
) -> None:
    """Calculate current storage consumption and verify quota limits."""
    total_used = (
        db.query(func.coalesce(func.sum(FileVersion.size_bytes), 0))
        .join(FileModel, FileVersion.file_id == FileModel.id)
        .filter(FileModel.owner_id == user_id)
        .scalar()
    )
    if total_used + new_file_bytes > quota_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Storage quota limit exceeded",
        )


def _store_version(
    db: Session,
    file_row: FileModel,
    data: bytes,
    content_type: str,
    user_id: int,
    username: str,
    storage: Storage,
    *,
    action: str,
    details: str | None = None,
) -> int:
    version_number = file_row.current_version + 1
    blob_name = f"owner/{file_row.id}/v{version_number}"

    try:
        storage.upload(blob_name, data, content_type)

        db.add(
            FileVersion(
                file_id=file_row.id,
                version_number=version_number,
                size_bytes=len(data),
                content_type=content_type,
                blob_name=blob_name,
                created_by=user_id,
            )
        )
        file_row.current_version = version_number
        file_row.content_type = content_type

        write_log(
            db,
            action=action,
            username=username,
            resource=f"file:{file_row.id}/v{version_number}",
            details=details,
        )
        db.commit()
    except IntegrityError:
        db.rollback()
        _delete_blob(storage, blob_name)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Version conflicts with an existing record",
        )
    except Exception:
        db.rollback()
        _delete_blob(storage, blob_name)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to store file binary data",
        )

    return version_number


@router.post(
    "/upload",
    response_model=FileOut,
    status_code=status.HTTP_201_CREATED,
)
def upload_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("write")),
    storage: Storage = Depends(get_storage),
):
    safe_name = _safe_filename(file.filename)
    data, content_type = _read_upload(file)

    _check_user_quota(db, current_user.id, current_user.quota_bytes, len(data))

    existing = (
        db.query(FileModel)
        .filter(
            FileModel.owner_id == current_user.id,
            FileModel.filename == safe_name,
        )
        .first()
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "File already exists in your account. "
                f"Use POST /files/{existing.id}/versions to update"
            ),
        )

    file_row = FileModel(
        owner_id=current_user.id,
        filename=safe_name,
        content_type=content_type,
        current_version=0,
    )
    db.add(file_row)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="File record conflict",
        )

    _store_version(
        db,
        file_row,
        data,
        content_type,
        current_user.id,
        current_user.username,
        storage,
        action="UPLOAD_NEW",
    )

    db.refresh(file_row)
    return _file_out(db, file_row)


@router.post(
    "/{file_id}/versions",
    response_model=FileOut,
    status_code=status.HTTP_201_CREATED,
)
def create_version(
    file_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("update")),
    storage: Storage = Depends(get_storage),
):
    file_row = get_file_with_access(
        db, file_id, current_user, required_level="editor", for_update=True
    )
    data, content_type = _read_upload(file)

    owner = db.query(User).filter(User.id == file_row.owner_id).first()
    if owner:
        _check_user_quota(db, owner.id, owner.quota_bytes, len(data))

    _store_version(
        db,
        file_row,
        data,
        content_type,
        current_user.id,
        current_user.username,
        storage,
        action="UPLOAD_VERSION",
    )

    db.refresh(file_row)
    return _file_out(db, file_row)


@router.get("", response_model=list[FileOut])
def list_files(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("read")),
):
    files = (
        db.query(FileModel)
        .filter(
            FileModel.owner_id == current_user.id,
            FileModel.deleted_at.is_(None),
        )
        .order_by(FileModel.created_at.desc())
        .all()
    )

    result = [_file_out(db, file) for file in files]

    write_log(
        db,
        action="LIST",
        username=current_user.username,
        resource="files",
    )
    db.commit()
    return result


@router.get("/{file_id}/download")
def download_file(
    file_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("read")),
    storage: Storage = Depends(get_storage),
):
    file_row = get_file_with_access(
        db, file_id, current_user, required_level="reader"
    )

    version = (
        db.query(FileVersion)
        .filter(
            FileVersion.file_id == file_row.id,
            FileVersion.version_number == file_row.current_version,
        )
        .first()
    )
    if version is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File version not found",
        )

    try:
        data = storage.download(version.blob_name)
    except Exception:
        write_log(
            db,
            action="DOWNLOAD",
            username=current_user.username,
            resource=f"file:{file_row.id}/v{file_row.current_version}",
            result="FAIL",
            details="Could not read file from storage provider",
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not download file",
        )

    write_log(
        db,
        action="DOWNLOAD",
        username=current_user.username,
        resource=f"file:{file_row.id}/v{file_row.current_version}",
    )
    db.commit()

    return Response(
        content=data,
        media_type=version.content_type
        or file_row.content_type
        or "application/octet-stream",
        headers={
            "Content-Disposition": _content_disposition(file_row.filename),
        },
    )


@router.get("/{file_id}/versions", response_model=list[FileVersionOut])
def list_versions(
    file_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("read")),
):
    file_row = get_file_with_access(
        db, file_id, current_user, required_level="reader"
    )

    versions = (
        db.query(FileVersion)
        .filter(FileVersion.file_id == file_row.id)
        .order_by(FileVersion.version_number.desc())
        .all()
    )

    result = [_version_out(version) for version in versions]

    write_log(
        db,
        action="LIST_VERSIONS",
        username=current_user.username,
        resource=f"file:{file_row.id}",
    )
    db.commit()
    return result


@router.get("/{file_id}/versions/{version_number}/download")
def download_version(
    file_id: int,
    version_number: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("read")),
    storage: Storage = Depends(get_storage),
):
    file_row = get_file_with_access(
        db, file_id, current_user, required_level="reader"
    )

    version = (
        db.query(FileVersion)
        .filter(
            FileVersion.file_id == file_row.id,
            FileVersion.version_number == version_number,
        )
        .first()
    )
    if version is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Specified version not found",
        )

    try:
        data = storage.download(version.blob_name)
    except Exception:
        write_log(
            db,
            action="DOWNLOAD_VERSION",
            username=current_user.username,
            resource=f"file:{file_row.id}/v{version_number}",
            result="FAIL",
            details="Could not read version from storage provider",
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not download version",
        )

    write_log(
        db,
        action="DOWNLOAD_VERSION",
        username=current_user.username,
        resource=f"file:{file_row.id}/v{version_number}",
    )
    db.commit()

    return Response(
        content=data,
        media_type=version.content_type
        or file_row.content_type
        or "application/octet-stream",
        headers={
            "Content-Disposition": _content_disposition(file_row.filename),
        },
    )


@router.post(
    "/{file_id}/versions/{version_number}/restore",
    response_model=FileOut,
    status_code=status.HTTP_201_CREATED,
)
def restore_version(
    file_id: int,
    version_number: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("update")),
    storage: Storage = Depends(get_storage),
):
    file_row = get_file_with_access(
        db, file_id, current_user, required_level="editor", for_update=True
    )

    old_version = (
        db.query(FileVersion)
        .filter(
            FileVersion.file_id == file_row.id,
            FileVersion.version_number == version_number,
        )
        .first()
    )
    if old_version is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Version not found",
        )

    try:
        data = storage.download(old_version.blob_name)
    except Exception:
        write_log(
            db,
            action="RESTORE_VERSION",
            username=current_user.username,
            resource=f"file:{file_row.id}/v{version_number}",
            result="FAIL",
            details="Could not read version from storage provider",
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not restore version",
        )

    content_type = (
        old_version.content_type
        or file_row.content_type
        or "application/octet-stream"
    )
    _store_version(
        db,
        file_row,
        data,
        content_type,
        current_user.id,
        current_user.username,
        storage,
        action="RESTORE_VERSION",
        details=f"Restored version {version_number}",
    )

    db.refresh(file_row)
    return _file_out(db, file_row)


@router.delete("/{file_id}")
def soft_delete_file(
    file_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("write")),
):
    """Move a file to trash."""
    file_row = get_file_with_access(
        db, file_id, current_user, required_level="manager"
    )
    file_row.deleted_at = datetime.now(timezone.utc)

    write_log(
        db,
        action="TRASH_FILE",
        username=current_user.username,
        resource=f"file:{file_id}",
    )
    db.commit()
    return {"detail": "File moved to trash"}


@router.post("/{file_id}/restore")
def restore_file(
    file_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("write")),
):
    """Restore a file from trash."""
    file_row = get_file_with_access(
        db, file_id, current_user, required_level="manager", include_deleted=True
    )
    if file_row.deleted_at is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File is not in trash",
        )

    file_row.deleted_at = None
    write_log(
        db,
        action="RESTORE_FILE",
        username=current_user.username,
        resource=f"file:{file_id}",
    )
    db.commit()
    return {"detail": "File restored successfully"}


@router.post("/{file_id}/share", status_code=status.HTTP_201_CREATED)
def share_file(
    file_id: int,
    payload: FileShareCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("write")),
):
    """Grant access level (reader, editor, manager) to another user."""
    file_row = get_file_with_access(
        db, file_id, current_user, required_level="manager"
    )

    target_user = (
        db.query(User).filter(User.username == payload.granted_to_username).first()
    )
    if target_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Target user not found"
        )

    if target_user.id == file_row.owner_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot share file with its owner",
        )

    existing_share = (
        db.query(FileShare)
        .filter(
            FileShare.file_id == file_id, FileShare.granted_to == target_user.id
        )
        .first()
    )
    if existing_share is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Access already granted to this user",
        )

    share = FileShare(
        file_id=file_row.id,
        granted_to=target_user.id,
        granted_by=current_user.id,
        access_level=payload.access_level,
    )
    db.add(share)
    write_log(
        db,
        action="SHARE_FILE",
        username=current_user.username,
        resource=f"file:{file_id}->user:{target_user.username}",
        details=f"level:{payload.access_level}",
    )
    db.commit()
    return {
        "detail": f"File shared with {target_user.username} as {payload.access_level}"
    }


@router.delete("/{file_id}/share/{target_user_id}")
def revoke_share(
    file_id: int,
    target_user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("write")),
):
    """Revoke user access to a shared file."""
    file_row = get_file_with_access(
        db, file_id, current_user, required_level="manager"
    )

    share = (
        db.query(FileShare)
        .filter(
            FileShare.file_id == file_row.id,
            FileShare.granted_to == target_user_id,
        )
        .first()
    )
    if share is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Share permission not found",
        )

    db.delete(share)
    write_log(
        db,
        action="REVOKE_SHARE",
        username=current_user.username,
        resource=f"file:{file_id}->user_id:{target_user_id}",
    )
    db.commit()
    return {"detail": "Share revoked successfully"}

@router.get("/shared", response_model=list[FileOut])
def list_shared_files(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("read")),
):
    """List all files that have been shared with the current user."""
    files = (
        db.query(FileModel)
        .join(FileShare, FileModel.id == FileShare.file_id)
        .filter(
            FileShare.granted_to == current_user.id,
            FileModel.deleted_at.is_(None),
        )
        .order_by(FileModel.created_at.desc())
        .all()
    )

    result = [_file_out(db, file) for file in files]

    write_log(
        db,
        action="LIST_SHARED",
        username=current_user.username,
        resource="files/shared",
    )
    db.commit()
    return result


@router.get("/trash", response_model=list[FileOut])
def list_trash_files(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("read")),
):
    """List all files currently in the user's trash bin."""
    files = (
        db.query(FileModel)
        .filter(
            FileModel.owner_id == current_user.id,
            FileModel.deleted_at.is_not(None),
        )
        .order_by(FileModel.deleted_at.desc())
        .all()
    )

    result = [_file_out(db, file) for file in files]

    write_log(
        db,
        action="LIST_TRASH",
        username=current_user.username,
        resource="files/trash",
    )
    db.commit()
    return result


@router.delete("/{file_id}/permanent")
def permanently_delete_file(
    file_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("write")),
    storage: Storage = Depends(get_storage),
):
    """Permanently purge a file and all its blob versions from Azure storage and DB."""
    file_row = get_file_with_access(
        db, file_id, current_user, required_level="manager", include_deleted=True
    )

    if not current_user.is_admin and file_row.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the file owner or admin can permanently purge it",
        )

    versions = db.query(FileVersion).filter(FileVersion.file_id == file_row.id).all()
    for version in versions:
        _delete_blob(storage, version.blob_name)

    write_log(
        db,
        action="PERMANENT_DELETE",
        username=current_user.username,
        resource=f"file:{file_id}",
    )
    db.delete(file_row)
    db.commit()
    return {"detail": "File and version history permanently deleted"}