from app.models import User
from app.security import hash_password


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


def _upload(client, token: str, filename: str, content: bytes):
    return client.post(
        "/files/upload",
        headers=_auth(token),
        files={"file": (filename, content, "text/plain")},
    )


def _version(client, token: str, file_id: int, content: bytes):
    return client.post(
        f"/files/{file_id}/versions",
        headers=_auth(token),
        files={"file": ("version.txt", content, "text/plain")},
    )


def test_admin_can_list_all_users_and_files(client, db_session, storage):
    admin = _create_user(db_session, "admin1", is_admin=True)
    owner = _create_user(db_session, "owner3", can_write=True)
    owner_token = _login(client, "owner3")
    admin_token = _login(client, "admin1")

    upload = _upload(client, owner_token, "compartido.txt", b"datos")
    assert upload.status_code == 201

    users = client.get("/admin/users", headers=_auth(admin_token))
    assert users.status_code == 200
    usernames = {user["username"] for user in users.json()}
    assert {"admin1", "owner3"} <= usernames

    files = client.get("/admin/files", headers=_auth(admin_token))
    assert files.status_code == 200
    assert any(
        file["id"] == upload.json()["id"]
        and file["owner_username"] == "owner3"
        for file in files.json()
    )

    forbidden = client.get("/admin/users", headers=_auth(owner_token))
    assert forbidden.status_code == 403

    assert admin.is_admin is True
    assert owner.is_admin is False


def test_admin_can_update_and_download_any_file(client, db_session, storage):
    _create_user(db_session, "admin2", is_admin=True)
    _create_user(db_session, "owner4", can_write=True)
    owner_token = _login(client, "owner4")
    admin_token = _login(client, "admin2")

    upload = _upload(client, owner_token, "ajeno.txt", b"original")
    assert upload.status_code == 201
    file_id = upload.json()["id"]

    version = _version(client, admin_token, file_id, b"version admin")
    assert version.status_code == 201
    assert version.json()["current_version"] == 2
    assert version.json()["owner_username"] == "owner4"

    download = client.get(f"/files/{file_id}/download", headers=_auth(owner_token))
    assert download.status_code == 200
    assert download.content == b"version admin"


def test_admin_can_restore_any_file(client, db_session, storage):
    _create_user(db_session, "admin3", is_admin=True)
    _create_user(
        db_session,
        "owner5",
        can_write=True,
        can_update=True,
    )
    owner_token = _login(client, "owner5")
    admin_token = _login(client, "admin3")

    upload = _upload(client, owner_token, "restaurar-admin.txt", b"uno")
    assert upload.status_code == 201
    file_id = upload.json()["id"]

    assert _version(client, owner_token, file_id, b"dos").status_code == 201

    restored = client.post(
        f"/files/{file_id}/versions/1/restore",
        headers=_auth(admin_token),
    )
    assert restored.status_code == 201
    assert restored.json()["current_version"] == 3

    download = client.get(f"/files/{file_id}/download", headers=_auth(owner_token))
    assert download.status_code == 200
    assert download.content == b"uno"


def test_admin_can_revoke_permissions(client, db_session, storage):
    _create_user(db_session, "admin4", is_admin=True)
    user = _create_user(
        db_session,
        "revocable1",
        can_read=True,
        can_write=True,
        can_update=True,
    )
    admin_token = _login(client, "admin4")
    user_token = _login(client, "revocable1")

    upload = _upload(client, user_token, "revocable.txt", b"uno")
    assert upload.status_code == 201
    file_id = upload.json()["id"]

    response = client.patch(
        f"/admin/users/{user.id}/permissions",
        headers=_auth(admin_token),
        json={"can_update": False},
    )
    assert response.status_code == 200
    assert response.json()["can_update"] is False

    denied = _version(client, user_token, file_id, b"dos")
    assert denied.status_code == 403

    response = client.patch(
        f"/admin/users/{user.id}/permissions",
        headers=_auth(admin_token),
        json={"can_read": False},
    )
    assert response.status_code == 200
    assert response.json()["can_read"] is False

    denied = client.get("/files", headers=_auth(user_token))
    assert denied.status_code == 403

    response = client.patch(
        f"/admin/users/{user.id}/permissions",
        headers=_auth(admin_token),
        json={"can_write": False},
    )
    assert response.status_code == 200
    assert response.json()["can_write"] is False

    denied = _upload(client, user_token, "nuevo.txt", b"datos")
    assert denied.status_code == 403


def test_admin_permission_update_rejects_privilege_fields(client, db_session, storage):
    _create_user(db_session, "admin5", is_admin=True)
    user = _create_user(db_session, "normal1")
    admin_token = _login(client, "admin5")

    response = client.patch(
        f"/admin/users/{user.id}/permissions",
        headers=_auth(admin_token),
        json={"is_admin": True},
    )
    assert response.status_code == 422


def test_admin_endpoints_require_admin(client, db_session, storage):
    _create_user(db_session, "normal2", can_read=True)
    token = _login(client, "normal2")

    assert client.get("/admin/users", headers=_auth(token)).status_code == 403
    assert client.get("/admin/files", headers=_auth(token)).status_code == 403
