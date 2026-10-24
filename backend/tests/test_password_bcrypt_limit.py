"""bcrypt accepts at most 72 UTF-8 bytes; the API must reject longer passwords before hashing."""

VALID_EMAIL = "bcrypt-limit@example.com"
PASSWORD_72_BYTES = "a" * 72
PASSWORD_73_BYTES = "a" * 73


def test_register_accepts_password_at_72_byte_limit(client):
    response = client.post(
        "/api/auth/register",
        json={"email": VALID_EMAIL, "password": PASSWORD_72_BYTES},
    )
    assert response.status_code == 201


def test_register_rejects_password_over_72_bytes(client):
    response = client.post(
        "/api/auth/register",
        json={"email": "over-limit@example.com", "password": PASSWORD_73_BYTES},
    )
    assert response.status_code == 422


def test_login_rejects_password_over_72_bytes(client):
    response = client.post(
        "/api/auth/login",
        json={"email": VALID_EMAIL, "password": PASSWORD_73_BYTES},
    )
    assert response.status_code == 422
