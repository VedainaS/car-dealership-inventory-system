"""Login endpoint tests."""

VALID_PASSWORD = "SecurePass123!"


def _register(client, email: str, password: str = VALID_PASSWORD):
    return client.post("/api/auth/register", json={"email": email, "password": password})


def test_login_success(client):
    email = "login-ok@example.com"
    _register(client, email)

    response = client.post(
        "/api/auth/login",
        json={"email": email, "password": VALID_PASSWORD},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert isinstance(body["access_token"], str)
    assert len(body["access_token"]) > 0


def test_login_incorrect_password(client):
    email = "wrong-pass@example.com"
    _register(client, email)

    response = client.post(
        "/api/auth/login",
        json={"email": email, "password": "WrongPassword999!"},
    )
    assert response.status_code == 401
    assert "detail" in response.json()


def test_login_unknown_email(client):
    response = client.post(
        "/api/auth/login",
        json={"email": "nobody@example.com", "password": VALID_PASSWORD},
    )
    assert response.status_code == 401


def test_login_invalid_input(client):
    response = client.post(
        "/api/auth/login",
        json={"email": "bad-email", "password": ""},
    )
    assert response.status_code == 422
