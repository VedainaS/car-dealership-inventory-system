"""The SPA needs to identify its signed-in user and call the API across ports."""

from app.models import User, UserRole


def test_current_user_endpoint_returns_database_role(client, db_session):
    email = "admin-me@example.com"
    password = "SecurePass123!"
    assert client.post("/api/auth/register", json={"email": email, "password": password}).status_code == 201
    user = db_session.query(User).filter_by(email=email).one()
    user.role = UserRole.ADMIN
    db_session.commit()
    token = client.post("/api/auth/login", json={"email": email, "password": password}).json()["access_token"]

    response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["role"] == "admin"
    assert response.json()["email"] == email


def test_current_user_requires_authentication(client):
    assert client.get("/api/auth/me").status_code == 401


def test_local_frontend_preflight_is_allowed(client):
    response = client.options(
        "/api/vehicles",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "authorization",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
