"""Registration endpoint tests."""

VALID_PASSWORD = "SecurePass123!"


def test_register_success(client):
    response = client.post(
        "/api/auth/register",
        json={"email": "buyer@example.com", "password": VALID_PASSWORD},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "buyer@example.com"
    assert body["role"] == "user"
    assert "id" in body
    assert "password" not in body
    assert "hashed_password" not in body


def test_register_duplicate_email(client):
    payload = {"email": "dup@example.com", "password": VALID_PASSWORD}
    first = client.post("/api/auth/register", json=payload)
    assert first.status_code == 201

    second = client.post("/api/auth/register", json=payload)
    assert second.status_code == 409
    assert "detail" in second.json()


def test_register_invalid_email(client):
    response = client.post(
        "/api/auth/register",
        json={"email": "not-an-email", "password": VALID_PASSWORD},
    )
    assert response.status_code == 422


def test_register_password_too_short(client):
    response = client.post(
        "/api/auth/register",
        json={"email": "short@example.com", "password": "abc"},
    )
    assert response.status_code == 422


def test_register_cannot_set_admin_role(client):
    response = client.post(
        "/api/auth/register",
        json={
            "email": "hacker@example.com",
            "password": VALID_PASSWORD,
            "role": "admin",
        },
    )
    assert response.status_code == 201
    assert response.json()["role"] == "user"
