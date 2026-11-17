import mimetypes
from datetime import datetime, timezone
from hashlib import sha256
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
from ..deps import get_file_with_access, require_permission
from ..logbook import write_log
from ..models import File as FileModel
from ..models import FileShare, FileVersion, User
from ..schemas import FileOut, FileShareCreate, FileShareOut, FileVersionOut
from ..storage import Storage, get_storage

router = APIRouter(prefix="/files", tags=["files"])


def _safe_filename(filename: str | None) -> str:
    name = (filename or "").replace("\\", "/").split("/")[-1]
    name = "".join(char for char in name if char.isprintable()).strip()
    if name in {"", ".", ".."}:
        return "file"
    return name[:255]


def _split_extension(filename: str) -> str | None:
    if "." in filename and not filename.startswith("."):
        return filename.rsplit(".", 1)[-1][:50]
    return None


def _guess_content_type(filename: str, fallback: str | None = None) -> str:
    guessed, _ = mimetypes.guess_type(filename)
    return guessed or fallback or "application/octet-stream"


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


def _latest_version(db: Session, file_id: int) -> FileVersion | None:
    return (
        db.query(FileVersion)
        .filter(FileVersion.file_id == file_id)
        .order_by(FileVersion.version_number.desc())
        .first()
    )


def _file_out(db: Session, file: FileModel) -> FileOut:
    version = _latest_version(db, file.file_id)
    return FileOut(
        file_id=file.file_id,
        filename=file.filename,
        extension=file.extension,
        owner_id=file.owner_id,
        owner_username=file.owner.username,
        deleted_at=file.deleted_at,
        current_version=version.version_number if version else None,
        size_bytes=version.size_bytes if version else 0,
        uploaded_at=version.uploaded_at if version else None,
        uploaded_by=version.uploaded_by if version else None,
    )


def _version_out(version: FileVersion) -> FileVersionOut:
    return FileVersionOut(
        file_id=version.file_id,
        version_number=version.version_number,
        blob_name=version.blob_name,
        uploaded_by=version.uploaded_by,
        uploaded_by_username=version.uploader.username,
        uploaded_at=version.uploaded_at,
        size_bytes=version.size_bytes,
        sha256=version.sha256,
    )


def _share_out(share: FileShare) -> FileShareOut:
    """Devuelve el nivel en los valores de la API (reader/editor/manager)."""
    level_map = {"lector": "reader", "editor": "editor", "gestor": "manager"}
    return FileShareOut(
        file_id=share.file_id,
        granted_to=share.granted_to,
        granted_to_username=share.receiver.username,
        granted_by=share.granted_by,
        granted_by_username=share.granter.username,
        access_level=level_map.get(share.access_level, share.access_level),
    )


def _verify_integrity(
    db: Session,
    version: FileVersion,
    data: bytes,
    current_user: User,
    file_row: FileModel,
    *,
    action: str,
) -> None:
    """Comprueba el SHA-256 guardado. Si no coincide, registra INTEGRITY_FAIL y responde 502."""
    if not version.sha256:
        return
    if sha256(data).hexdigest() == version.sha256:
        return

    write_log(
        db,
        action="INTEGRITY_FAIL",
        user_id=current_user.user_id,
        file_id=file_row.file_id,
        status="FAIL",
    )
    db.commit()
    raise HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail="File integrity check failed",
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
    total_used = (
        db.query(func.coalesce(func.sum(FileVersion.size_bytes), 0))
        .join(FileModel, FileVersion.file_id == FileModel.file_id)
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
    user: User,
    storage: Storage,
    *,
    action: str,
) -> int:
    latest = _latest_version(db, file_row.file_id)
    version_number = (latest.version_number if latest else 0) + 1
    blob_name = f"owner/{file_row.file_id}/v{version_number}"

    try:
        storage.upload(blob_name, data, content_type)
        db.add(
            FileVersion(
                file_id=file_row.file_id,
                version_number=version_number,
                blob_name=blob_name,
                uploaded_by=user.user_id,
                size_bytes=len(data),
                sha256=sha256(data).hexdigest(),
            )
        )
        write_log(
            db,
            action=action,
            user_id=user.user_id,
            file_id=file_row.file_id,
            status="OK",
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


@router.post("/upload", response_model=FileOut, status_code=status.HTTP_201_CREATED)
def upload_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("write")),
    storage: Storage = Depends(get_storage),
):
    safe_name = _safe_filename(file.filename)
    data, content_type = _read_upload(file)

    _check_user_quota(db, current_user.user_id, current_user.quota_bytes, len(data))

    existing = (
        db.query(FileModel)
        .filter(
            FileModel.owner_id == current_user.user_id,
            FileModel.filename == safe_name,
            FileModel.deleted_at.is_(None),
        )
        .first()
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "File already exists in your account. "
                f"Use POST /files/{existing.file_id}/versions to update"
            ),
        )

    file_row = FileModel(
        owner_id=current_user.user_id,
        filename=safe_name,
        extension=_split_extension(safe_name),
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
        current_user,
        storage,
        action="UPLOAD_NEW",
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
            FileModel.owner_id == current_user.user_id,
            FileModel.deleted_at.is_(None),
        )
        .order_by(FileModel.file_id.desc())
        .all()
    )

    result = [_file_out(db, file) for file in files]
    write_log(db, action="LIST", user_id=current_user.user_id, status="OK")
    db.commit()
    return result


@router.get("/shared", response_model=list[FileOut])
def list_shared_files(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("read")),
):
    files = (
        db.query(FileModel)
        .join(FileShare, FileModel.file_id == FileShare.file_id)
        .filter(
            FileShare.granted_to == current_user.user_id,
            FileModel.deleted_at.is_(None),
        )
        .order_by(FileModel.file_id.desc())
        .all()
    )

    result = [_file_out(db, file) for file in files]
    write_log(db, action="LIST_SHARED", user_id=current_user.user_id, status="OK")
    db.commit()
    return result


@router.get("/trash", response_model=list[FileOut])
def list_trash_files(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("read")),
):
    files = (
        db.query(FileModel)
        .filter(
            FileModel.owner_id == current_user.user_id,
            FileModel.deleted_at.is_not(None),
        )
        .order_by(FileModel.deleted_at.desc())
        .all()
    )

    result = [_file_out(db, file) for file in files]
    write_log(db, action="LIST_TRASH", user_id=current_user.user_id, status="OK")
    db.commit()
    return result


@router.post("/{file_id}/versions", response_model=FileOut, status_code=status.HTTP_201_CREATED)
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

    owner = db.query(User).filter(User.user_id == file_row.owner_id).first()
    if owner:
        _check_user_quota(db, owner.user_id, owner.quota_bytes, len(data))

    _store_version(
        db,
        file_row,
        data,
        content_type,
        current_user,
        storage,
        action="UPLOAD_VERSION",
    )

    db.refresh(file_row)
    return _file_out(db, file_row)


@router.get("/{file_id}/download")
def download_file(
    file_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("read")),
    storage: Storage = Depends(get_storage),
):
    file_row = get_file_with_access(db, file_id, current_user, required_level="reader")
    version = _latest_version(db, file_row.file_id)
    if version is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File version not found")

    try:
        data = storage.download(version.blob_name)
    except Exception:
        write_log(db, action="DOWNLOAD", user_id=current_user.user_id, file_id=file_row.file_id, status="FAIL")
        db.commit()
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Could not download file")

    _verify_integrity(db, version, data, current_user, file_row, action="DOWNLOAD")

    write_log(db, action="DOWNLOAD", user_id=current_user.user_id, file_id=file_row.file_id, status="OK")
    db.commit()

    return Response(
        content=data,
        media_type=_guess_content_type(file_row.filename),
        headers={"Content-Disposition": _content_disposition(file_row.filename)},
    )


@router.get("/{file_id}/versions", response_model=list[FileVersionOut])
def list_versions(
    file_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("read")),
):
    file_row = get_file_with_access(db, file_id, current_user, required_level="reader")
    versions = (
        db.query(FileVersion)
        .filter(FileVersion.file_id == file_row.file_id)
        .order_by(FileVersion.version_number.desc())
        .all()
    )
    result = [_version_out(version) for version in versions]
    write_log(db, action="LIST_VERSIONS", user_id=current_user.user_id, file_id=file_row.file_id, status="OK")
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
    file_row = get_file_with_access(db, file_id, current_user, required_level="reader")
    version = (
        db.query(FileVersion)
        .filter(
            FileVersion.file_id == file_row.file_id,
            FileVersion.version_number == version_number,
        )
        .first()
    )
    if version is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Specified version not found")

    try:
        data = storage.download(version.blob_name)
    except Exception:
        write_log(db, action="DOWNLOAD_VERSION", user_id=current_user.user_id, file_id=file_row.file_id, status="FAIL")
        db.commit()
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Could not download version")

    _verify_integrity(db, version, data, current_user, file_row, action="DOWNLOAD_VERSION")

    write_log(db, action="DOWNLOAD_VERSION", user_id=current_user.user_id, file_id=file_row.file_id, status="OK")
    db.commit()

    return Response(
        content=data,
        media_type=_guess_content_type(file_row.filename),
        headers={"Content-Disposition": _content_disposition(file_row.filename)},
    )


@router.post("/{file_id}/versions/{version_number}/restore", response_model=FileOut, status_code=status.HTTP_201_CREATED)
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
            FileVersion.file_id == file_row.file_id,
            FileVersion.version_number == version_number,
        )
        .first()
    )
    if old_version is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Version not found")

    try:
        data = storage.download(old_version.blob_name)
    except Exception:
        write_log(db, action="RESTORE_VERSION", user_id=current_user.user_id, file_id=file_row.file_id, status="FAIL")
        db.commit()
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Could not restore version")

    content_type = _guess_content_type(file_row.filename)
    _store_version(db, file_row, data, content_type, current_user, storage, action="RESTORE_VERSION")
    db.refresh(file_row)
    return _file_out(db, file_row)


@router.delete("/{file_id}")
def soft_delete_file(
    file_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("write")),
):
    file_row = get_file_with_access(db, file_id, current_user, required_level="manager")
    file_row.deleted_at = datetime.now(timezone.utc)
    write_log(db, action="TRASH_FILE", user_id=current_user.user_id, file_id=file_id, status="OK")
    db.commit()
    return {"detail": "File moved to trash"}


@router.post("/{file_id}/restore")
def restore_file(
    file_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("write")),
):
    file_row = get_file_with_access(
        db, file_id, current_user, required_level="manager", include_deleted=True
    )
    if file_row.deleted_at is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File is not in trash")

    file_row.deleted_at = None
    write_log(db, action="RESTORE_FILE", user_id=current_user.user_id, file_id=file_id, status="OK")
    db.commit()
    return {"detail": "File restored successfully"}


@router.get("/{file_id}/shares", response_model=list[FileShareOut])
def list_file_shares(
    file_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("read")),
):
    file_row = get_file_with_access(db, file_id, current_user, required_level="manager")
    shares = (
        db.query(FileShare)
        .filter(FileShare.file_id == file_row.file_id)
        .order_by(FileShare.granted_to)
        .all()
    )
    return [_share_out(share) for share in shares]


@router.post("/{file_id}/share", status_code=status.HTTP_201_CREATED)
def share_file(
    file_id: int,
    payload: FileShareCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("write")),
):
    file_row = get_file_with_access(db, file_id, current_user, required_level="manager")

    target_user = db.query(User).filter(User.username == payload.granted_to_username).first()
    if target_user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target user not found")

    if target_user.user_id == file_row.owner_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot share file with its owner")

    existing_share = (
        db.query(FileShare)
        .filter(FileShare.file_id == file_id, FileShare.granted_to == target_user.user_id)
        .first()
    )
    if existing_share is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Access already granted to this user")

    access_level = payload.access_level
    if access_level == "reader":
        access_level = "lector"
    elif access_level == "manager":
        access_level = "gestor"

    share = FileShare(
        file_id=file_row.file_id,
        granted_to=target_user.user_id,
        granted_by=current_user.user_id,
        access_level=access_level,
    )
    db.add(share)
    write_log(db, action="SHARE_FILE", user_id=current_user.user_id, file_id=file_id, status="OK")
    db.commit()
    return {"detail": f"File shared with {target_user.username} as {access_level}"}


@router.delete("/{file_id}/share/{target_user_id}")
def revoke_share(
    file_id: int,
    target_user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("write")),
):
    file_row = get_file_with_access(db, file_id, current_user, required_level="manager")

    share = (
        db.query(FileShare)
        .filter(FileShare.file_id == file_row.file_id, FileShare.granted_to == target_user_id)
        .first()
    )
    if share is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Share permission not found")

    db.delete(share)
    write_log(db, action="REVOKE_SHARE", user_id=current_user.user_id, file_id=file_id, status="OK")
    db.commit()
    return {"detail": "Share revoked successfully"}


@router.delete("/{file_id}/permanent")
def permanently_delete_file(
    file_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("write")),
    storage: Storage = Depends(get_storage),
):
    file_row = get_file_with_access(
        db, file_id, current_user, required_level="manager", include_deleted=True
    )

    if not current_user.is_admin and file_row.owner_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the file owner or admin can permanently purge it",
        )

    versions = db.query(FileVersion).filter(FileVersion.file_id == file_row.file_id).all()
    for version in versions:
        _delete_blob(storage, version.blob_name)

    write_log(db, action="PERMANENT_DELETE", user_id=current_user.user_id, file_id=file_id, status="OK")
    db.delete(file_row)
    db.commit()
    return {"detail": "File and version history permanently deleted"}