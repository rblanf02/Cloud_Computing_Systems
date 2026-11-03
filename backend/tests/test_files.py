from app.config import settings
from app.main import app as fastapi_app
from app.models import File as FileModel
from app.models import User
from app.security import hash_password
from app.storage import InMemoryStorage, get_storage


class FailingStorage(InMemoryStorage):
    def upload(self, blob_name: str, data: bytes, content_type: str | None) -> None:
        raise RuntimeError("fallo simulado del storage")


def _create_user(
    db_session,
    username: str,
    can_read: bool = True,
    can_write: bool = False,
    can_update: bool = False,
    is_admin: bool = False,
) -> User:
    user = User(
        username=username,
        email=f"{username}@example.com",
        hashed_password=hash_password("secreto123"),
        can_read=can_read,
        can_write=can_write,
        can_update=can_update,
        is_admin=is_admin,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _login(client, username: str) -> str:
    response = client.post(
        "/auth/login",
        json={"username": username, "password": "secreto123"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _upload_new(client, token: str, filename: str, content: bytes, content_type: str):
    return client.post(
        "/files/upload",
        headers=_auth(token),
        files={"file": (filename, content, content_type)},
    )


def _upload_version(
    client,
    token: str,
    file_id: int,
    content: bytes,
    content_type: str,
):
    return client.post(
        f"/files/{file_id}/versions",
        headers=_auth(token),
        files={"file": ("version.bin", content, content_type)},
    )


def test_create_list_and_download_file(client, db_session, storage):
    _create_user(db_session, "creator1", can_write=True)
    token = _login(client, "creator1")

    response = _upload_new(client, token, "foto.jpg", b"primera", "image/jpeg")
    assert response.status_code == 201
    data = response.json()
    assert data["filename"] == "foto.jpg"
    assert data["owner_username"] == "creator1"
    assert data["current_version"] == 1
    assert data["size_bytes"] == 7

    listed = client.get("/files", headers=_auth(token))
    assert listed.status_code == 200
    assert len(listed.json()) == 1
    assert listed.json()[0]["id"] == data["id"]

    download = client.get(f"/files/{data['id']}/download", headers=_auth(token))
    assert download.status_code == 200
    assert download.content == b"primera"
    assert download.headers["content-type"].startswith("image/jpeg")
    assert "foto.jpg" in download.headers["content-disposition"]


def test_duplicate_upload_returns_409_and_version_endpoint_works(
    client,
    db_session,
    storage,
):
    _create_user(db_session, "updater1", can_write=True, can_update=True)
    token = _login(client, "updater1")

    first = _upload_new(client, token, "nota.txt", b"uno", "text/plain")
    assert first.status_code == 201
    file_id = first.json()["id"]

    duplicate = _upload_new(client, token, "nota.txt", b"dos", "text/plain")
    assert duplicate.status_code == 409
    assert f"/files/{file_id}/versions" in duplicate.json()["detail"]

    version = _upload_version(client, token, file_id, b"dos", "text/plain")
    assert version.status_code == 201
    assert version.json()["id"] == file_id
    assert version.json()["current_version"] == 2
    assert version.json()["size_bytes"] == 3

    listed = client.get("/files", headers=_auth(token))
    assert listed.status_code == 200
    assert listed.json()[0]["current_version"] == 2

    download = client.get(f"/files/{file_id}/download", headers=_auth(token))
    assert download.status_code == 200
    assert download.content == b"dos"


def test_upload_requires_write_permission(client, db_session, storage):
    _create_user(db_session, "reader1", can_write=False)
    token = _login(client, "reader1")

    response = _upload_new(client, token, "documento.txt", b"datos", "text/plain")
    assert response.status_code == 403


def test_create_version_requires_update_permission(client, db_session, storage):
    _create_user(db_session, "writer1", can_write=True, can_update=False)
    token = _login(client, "writer1")

    upload = _upload_new(client, token, "documento.txt", b"datos", "text/plain")
    assert upload.status_code == 201

    response = _upload_version(
        client,
        token,
        upload.json()["id"],
        b"datos nuevos",
        "text/plain",
    )
    assert response.status_code == 403


def test_list_requires_read_permission(client, db_session, storage):
    _create_user(db_session, "nowrite1", can_read=False, can_write=True)
    token = _login(client, "nowrite1")

    response = client.get("/files", headers=_auth(token))
    assert response.status_code == 403


def test_upload_without_token_returns_401(client, storage):
    response = client.post(
        "/files/upload",
        files={"file": ("foto.jpg", b"datos", "image/jpeg")},
    )
    assert response.status_code == 401


def test_list_only_returns_own_files(client, db_session, storage):
    _create_user(db_session, "owner1", can_write=True)
    _create_user(db_session, "other1", can_write=True)

    owner_token = _login(client, "owner1")
    other_token = _login(client, "other1")

    upload = _upload_new(client, owner_token, "privado.txt", b"privado", "text/plain")
    assert upload.status_code == 201
    file_id = upload.json()["id"]

    listed = client.get("/files", headers=_auth(other_token))
    assert listed.status_code == 200
    assert listed.json() == []

    download = client.get(f"/files/{file_id}/download", headers=_auth(other_token))
    assert download.status_code == 404


def test_same_filename_allowed_for_different_users(client, db_session, storage):
    _create_user(db_session, "owner6", can_write=True, can_update=True)
    _create_user(db_session, "other6", can_write=True, can_update=True)

    owner_token = _login(client, "owner6")
    other_token = _login(client, "other6")

    first = _upload_new(client, owner_token, "informe.txt", b"de owner", "text/plain")
    second = _upload_new(client, other_token, "informe.txt", b"de other", "text/plain")
    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] != second.json()["id"]

    assert _upload_version(
        client,
        owner_token,
        first.json()["id"],
        b"version de owner",
        "text/plain",
    ).status_code == 201

    owner_download = client.get(
        f"/files/{first.json()['id']}/download",
        headers=_auth(owner_token),
    )
    other_download = client.get(
        f"/files/{second.json()['id']}/download",
        headers=_auth(other_token),
    )
    assert owner_download.content == b"version de owner"
    assert other_download.content == b"de other"


def test_create_version_for_other_user_returns_404(client, db_session, storage):
    _create_user(db_session, "owner2", can_write=True, can_update=True)
    _create_user(db_session, "other2", can_write=True, can_update=True)

    owner_token = _login(client, "owner2")
    other_token = _login(client, "other2")

    upload = _upload_new(client, owner_token, "privado.txt", b"privado", "text/plain")
    assert upload.status_code == 201

    response = _upload_version(
        client,
        other_token,
        upload.json()["id"],
        b"intento",
        "text/plain",
    )
    assert response.status_code == 404


def test_upload_sanitizes_filename(client, db_session, storage):
    _create_user(db_session, "sanitizer1", can_write=True)
    token = _login(client, "sanitizer1")

    response = _upload_new(client, token, "../malo.txt", b"datos", "text/plain")
    assert response.status_code == 201
    assert response.json()["filename"] == "malo.txt"


def test_upload_rejects_too_large_file(client, db_session, storage, monkeypatch):
    monkeypatch.setattr(settings, "max_upload_size_mb", 0)
    _create_user(db_session, "big1", can_write=True)
    token = _login(client, "big1")

    response = _upload_new(
        client,
        token,
        "grande.bin",
        b"x",
        "application/octet-stream",
    )
    assert response.status_code == 413


def test_upload_rolls_back_when_storage_fails(client, db_session):
    _create_user(db_session, "fail1", can_write=True)
    token = _login(client, "fail1")

    fastapi_app.dependency_overrides[get_storage] = lambda: FailingStorage()
    try:
        response = _upload_new(client, token, "fallo.txt", b"datos", "text/plain")
        assert response.status_code == 502
    finally:
        fastapi_app.dependency_overrides.pop(get_storage, None)

    db_session.expire_all()
    stored = (
        db_session.query(FileModel)
        .filter(FileModel.filename == "fallo.txt")
        .first()
    )
    assert stored is None


def test_version_history_and_download_old_version(client, db_session, storage):
    _create_user(
        db_session,
        "history1",
        can_read=True,
        can_write=True,
        can_update=True,
    )
    token = _login(client, "history1")

    upload = _upload_new(client, token, "historial.txt", b"uno", "text/plain")
    assert upload.status_code == 201
    file_id = upload.json()["id"]

    second = _upload_version(client, token, file_id, b"dos", "image/jpeg")
    assert second.status_code == 201

    versions = client.get(f"/files/{file_id}/versions", headers=_auth(token))
    assert versions.status_code == 200
    assert [item["version_number"] for item in versions.json()] == [2, 1]
    assert versions.json()[0]["content_type"] == "image/jpeg"
    assert versions.json()[1]["content_type"] == "text/plain"
    assert versions.json()[0]["created_by_username"] == "history1"

    old = client.get(
        f"/files/{file_id}/versions/1/download",
        headers=_auth(token),
    )
    assert old.status_code == 200
    assert old.content == b"uno"
    assert old.headers["content-type"].startswith("text/plain")

    latest = client.get(f"/files/{file_id}/download", headers=_auth(token))
    assert latest.status_code == 200
    assert latest.content == b"dos"
    assert latest.headers["content-type"].startswith("image/jpeg")


def test_restore_old_version_creates_new_version(client, db_session, storage):
    _create_user(
        db_session,
        "restore1",
        can_read=True,
        can_write=True,
        can_update=True,
    )
    token = _login(client, "restore1")

    upload = _upload_new(client, token, "restaurar.txt", b"uno", "text/plain")
    assert upload.status_code == 201
    file_id = upload.json()["id"]

    assert _upload_version(client, token, file_id, b"dos", "image/jpeg").status_code == 201
    assert _upload_version(client, token, file_id, b"tres", "text/plain").status_code == 201

    restored = client.post(
        f"/files/{file_id}/versions/1/restore",
        headers=_auth(token),
    )
    assert restored.status_code == 201
    assert restored.json()["current_version"] == 4

    latest = client.get(f"/files/{file_id}/download", headers=_auth(token))
    assert latest.status_code == 200
    assert latest.content == b"uno"
    assert latest.headers["content-type"].startswith("text/plain")

    versions = client.get(f"/files/{file_id}/versions", headers=_auth(token))
    assert [item["version_number"] for item in versions.json()] == [4, 3, 2, 1]

    old_second = client.get(
        f"/files/{file_id}/versions/2/download",
        headers=_auth(token),
    )
    assert old_second.status_code == 200
    assert old_second.content == b"dos"


def test_restore_requires_update_permission(client, db_session, storage):
    _create_user(db_session, "restorer1", can_read=True, can_write=True)
    token = _login(client, "restorer1")

    upload = _upload_new(client, token, "restaurar.txt", b"uno", "text/plain")
    assert upload.status_code == 201

    response = client.post(
        f"/files/{upload.json()['id']}/versions/1/restore",
        headers=_auth(token),
    )
    assert response.status_code == 403
