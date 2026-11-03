from datetime import datetime, timedelta, timezone

from app.models import UserSession
from app.security import create_access_token


def _register_and_login(client, username: str) -> str:
    client.post(
        "/auth/register",
        json={
            "username": username,
            "email": f"{username}@example.com",
            "password": "secreto123",
        },
    )
    response = client.post(
        "/auth/login",
        json={"username": username, "password": "secreto123"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_register_and_login(client):
    response = client.post(
        "/auth/register",
        json={"username": "maria", "email": "maria@example.com", "password": "secreto123"},
    )
    assert response.status_code == 201
    assert response.json()["username"] == "maria"
    assert "hashed_password" not in response.json()

    response = client.post(
        "/auth/login",
        json={"username": "maria", "password": "secreto123"},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]

    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["username"] == "maria"


def test_register_default_permissions(client):
    response = client.post(
        "/auth/register",
        json={"username": "ana", "email": "ana@example.com", "password": "secreto123"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["can_read"] is True
    assert data["can_write"] is False
    assert data["can_update"] is False
    assert data["is_admin"] is False


def test_register_cannot_assign_privileges(client):
    response = client.post(
        "/auth/register",
        json={
            "username": "intruso",
            "email": "intruso@example.com",
            "password": "secreto123",
            "is_admin": True,
            "can_write": True,
            "can_update": True,
        },
    )
    assert response.status_code == 422


def test_login_wrong_password(client):
    client.post(
        "/auth/register",
        json={"username": "ruben", "email": "ruben@example.com", "password": "buena123"},
    )
    response = client.post(
        "/auth/login",
        json={"username": "ruben", "password": "incorrecta"},
    )
    assert response.status_code == 401


def test_register_duplicate_username(client):
    payload = {"username": "diego", "email": "diego@example.com", "password": "secreto123"}
    first = client.post("/auth/register", json=payload)
    assert first.status_code == 201
    second = client.post("/auth/register", json=payload)
    assert second.status_code == 400


def test_me_without_token(client):
    response = client.get("/auth/me")
    assert response.status_code == 401


def test_me_with_invalid_bearer_token(client):
    response = client.get(
        "/auth/me",
        headers={"Authorization": "Bearer esto-no-es-un-jwt"},
    )
    assert response.status_code == 401


def test_me_with_wrong_auth_scheme(client):
    response = client.get(
        "/auth/me",
        headers={"Authorization": "Basic dXNlcjpwYXNz"},
    )
    assert response.status_code == 401


def test_logout(client):
    client.post(
        "/auth/register",
        json={"username": "nico", "email": "nico@example.com", "password": "secreto123"},
    )
    token = client.post(
        "/auth/login",
        json={"username": "nico", "password": "secreto123"},
    ).json()["access_token"]

    response = client.post("/auth/logout", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200

    reused = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert reused.status_code == 401


def test_logout_only_revokes_current_session(client):
    first_token = _register_and_login(client, "sesion1")
    second_token = _register_and_login(client, "sesion1")

    response = client.post(
        "/auth/logout",
        headers={"Authorization": f"Bearer {first_token}"},
    )
    assert response.status_code == 200

    first_reused = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {first_token}"},
    )
    assert first_reused.status_code == 401

    second_still_valid = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {second_token}"},
    )
    assert second_still_valid.status_code == 200


def test_session_expires_after_inactivity(client, db_session):
    token = _register_and_login(client, "sesion2")
    session = (
        db_session.query(UserSession)
        .order_by(UserSession.created_at.desc())
        .first()
    )
    assert session is not None

    session.last_activity_at = datetime.now(timezone.utc) - timedelta(minutes=11)
    db_session.commit()

    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401
    assert response.json()["detail"] == "Sesion expirada por inactividad"

    db_session.expire_all()
    db_session.refresh(session)
    assert session.revoked_at is not None


def test_activity_extends_session(client, db_session):
    token = _register_and_login(client, "sesion3")
    session = (
        db_session.query(UserSession)
        .order_by(UserSession.created_at.desc())
        .first()
    )
    assert session is not None

    old_activity = datetime.now(timezone.utc) - timedelta(minutes=9)
    session.last_activity_at = old_activity
    db_session.commit()

    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200

    db_session.expire_all()
    db_session.refresh(session)
    assert session.last_activity_at > old_activity


def test_token_without_session_id_is_rejected(client):
    client.post(
        "/auth/register",
        json={
            "username": "sesion4",
            "email": "sesion4@example.com",
            "password": "secreto123",
        },
    )
    token = create_access_token({"sub": "sesion4"})

    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401
