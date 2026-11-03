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
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..deps import get_owned_file, require_permission
from ..logbook import write_log
from ..models import File as FileModel
from ..models import FileVersion, User
from ..schemas import FileOut, FileVersionOut
from ..storage import Storage, get_storage

router = APIRouter(prefix="/files", tags=["files"])


def _safe_filename(filename: str | None) -> str:
    name = (filename or "").replace("\\", "/").split("/")[-1]
    name = "".join(char for char in name if char.isprintable()).strip()
    if name in {"", ".", ".."}:
        return "archivo"
    return name[:255]


def _content_disposition(filename: str) -> str:
    fallback = filename.encode("ascii", "ignore").decode().replace('"', "_")
    fallback = fallback or "archivo"
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
            detail=f"El fichero supera el limite de {settings.max_upload_size_mb} MB",
        )
    return data, file.content_type or "application/octet-stream"


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
            detail="La version esta en conflicto",
        )
    except Exception:
        db.rollback()
        _delete_blob(storage, blob_name)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="No se pudo guardar el fichero",
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
                "Ya tienes un fichero con ese nombre; "
                f"usa POST /files/{existing.id}/versions"
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
            detail="El fichero ya existe",
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
    file_row = get_owned_file(db, file_id, current_user, for_update=True)
    data, content_type = _read_upload(file)

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
        .filter(FileModel.owner_id == current_user.id)
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
    file_row = get_owned_file(db, file_id, current_user)

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
            detail="Version no encontrada",
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
            details="No se pudo leer el fichero del storage",
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="No se pudo descargar el fichero",
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
        media_type=version.content_type or file_row.content_type or "application/octet-stream",
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
    file_row = get_owned_file(db, file_id, current_user)

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
    file_row = get_owned_file(db, file_id, current_user)

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
            detail="Version no encontrada",
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
            details="No se pudo leer la version del storage",
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="No se pudo descargar la version",
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
        media_type=version.content_type or file_row.content_type or "application/octet-stream",
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
    file_row = get_owned_file(db, file_id, current_user, for_update=True)

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
            detail="Version no encontrada",
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
            details="No se pudo leer la version del storage",
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="No se pudo restaurar la version",
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
        details=f"Restaurada la version {version_number}",
    )

    db.refresh(file_row)
    return _file_out(db, file_row)
