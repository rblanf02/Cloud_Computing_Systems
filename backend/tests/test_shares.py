from app.models import User
from app.security import hash_password


def _create_user(
    db_session,
    username: str,
    is_admin: bool = False,
) -> User:
    user = User(
        username=username,
        email=f"{username}@example.com",
        hashed_password=hash_password("secreto123"),
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


def test_owner_can_share_list_and_revoke(client, db_session, storage):
    owner = _create_user(db_session, "shareowner")
    receiver = _create_user(db_session, "sharereceiver")
    owner_token = _login(client, "shareowner")
    receiver_token = _login(client, "sharereceiver")

    upload = _upload(client, owner_token, "compartido.txt", b"contenido")
    assert upload.status_code == 201
    file_id = upload.json()["file_id"]

    share = client.post(
        f"/files/{file_id}/share",
        headers=_auth(owner_token),
        json={"granted_to_username": "sharereceiver", "access_level": "reader"},
    )
    assert share.status_code == 201

    shares = client.get(f"/files/{file_id}/shares", headers=_auth(owner_token))
    assert shares.status_code == 200
    assert len(shares.json()) == 1
    assert shares.json()[0]["granted_to"] == receiver.user_id
    assert shares.json()[0]["granted_to_username"] == "sharereceiver"
    assert shares.json()[0]["granted_by_username"] == "shareowner"
    assert shares.json()[0]["access_level"] == "reader"

    shared = client.get("/files/shared", headers=_auth(receiver_token))
    assert shared.status_code == 200
    assert [item["file_id"] for item in shared.json()] == [file_id]

    download = client.get(f"/files/{file_id}/download", headers=_auth(receiver_token))
    assert download.status_code == 200
    assert download.content == b"contenido"

    assert owner.user_id is not None

    revoke = client.delete(
        f"/files/{file_id}/share/{receiver.user_id}",
        headers=_auth(owner_token),
    )
    assert revoke.status_code == 200

    after = client.get("/files/shared", headers=_auth(receiver_token))
    assert after.status_code == 200
    assert after.json() == []

    denied = client.get(f"/files/{file_id}/download", headers=_auth(receiver_token))
    assert denied.status_code == 404


def test_receiver_cannot_manage_shares(client, db_session, storage):
    _create_user(db_session, "shareowner2")
    _create_user(db_session, "sharereader2")
    owner_token = _login(client, "shareowner2")
    reader_token = _login(client, "sharereader2")

    upload = _upload(client, owner_token, "solo-lectura.txt", b"datos")
    assert upload.status_code == 201
    file_id = upload.json()["file_id"]

    assert client.post(
        f"/files/{file_id}/share",
        headers=_auth(owner_token),
        json={"granted_to_username": "sharereader2", "access_level": "reader"},
    ).status_code == 201

    response = client.get(f"/files/{file_id}/shares", headers=_auth(reader_token))
    assert response.status_code == 403
