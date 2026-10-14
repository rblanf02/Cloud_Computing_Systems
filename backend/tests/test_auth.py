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
