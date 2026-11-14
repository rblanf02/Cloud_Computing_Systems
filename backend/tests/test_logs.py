import csv
import json
from io import StringIO

from app.models import User
from app.security import hash_password


def _create_user(
    db_session,
    username: str,
    can_read: bool = True,
    can_write: bool = True,
    can_update: bool = True,
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


def _upload(client, token: str, filename: str):
    return client.post(
        "/files/upload",
        headers=_auth(token),
        files={"file": (filename, b"datos", "text/plain")},
    )


def test_regular_user_only_sees_own_logs(client, db_session, storage):
    _create_user(db_session, "loguser1")
    _create_user(db_session, "loguser2")
    token1 = _login(client, "loguser1")
    token2 = _login(client, "loguser2")

    assert _upload(client, token1, "uno.txt").status_code == 201

    logs1 = client.get("/logs", headers=_auth(token1))
    assert logs1.status_code == 200
    assert logs1.json()
    assert all(item["username"] == "loguser1" for item in logs1.json())
    assert any(item["action"] == "UPLOAD_NEW" for item in logs1.json())

    logs2 = client.get("/logs", headers=_auth(token2))
    assert logs2.status_code == 200
    assert all(item["username"] == "loguser2" for item in logs2.json())
    assert all(item["action"] != "UPLOAD_NEW" for item in logs2.json())


def test_admin_sees_all_logs(client, db_session, storage):
    _create_user(db_session, "loguser3")
    _create_user(db_session, "logadmin", is_admin=True)
    user_token = _login(client, "loguser3")
    admin_token = _login(client, "logadmin")

    assert _upload(client, user_token, "visible.txt").status_code == 201

    logs = client.get("/logs", headers=_auth(admin_token))
    assert logs.status_code == 200
    usernames = {item["username"] for item in logs.json()}
    assert {"loguser3", "logadmin"} <= usernames


def test_export_logs_json_and_csv(client, db_session, storage):
    _create_user(db_session, "loguser4")
    token = _login(client, "loguser4")
    assert _upload(client, token, "export.txt").status_code == 201

    response = client.get("/logs/export?fmt=json", headers=_auth(token))
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert "logbook.json" in response.headers["content-disposition"]
    rows = json.loads(response.text)
    assert rows
    assert all(item["username"] == "loguser4" for item in rows)

    response = client.get("/logs/export?fmt=csv", headers=_auth(token))
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "logbook.csv" in response.headers["content-disposition"]
    parsed = list(csv.DictReader(StringIO(response.text)))
    assert parsed
    assert all(item["username"] == "loguser4" for item in parsed)

    invalid = client.get("/logs/export?fmt=xml", headers=_auth(token))
    assert invalid.status_code == 400
