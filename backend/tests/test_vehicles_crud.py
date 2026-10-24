"""Phase 2 – Vehicle CRUD: auth guards, role enforcement, validation, happy paths.

Design contract
---------------
GET  /api/vehicles       – authenticated (any role); includes out-of-stock vehicles
POST /api/vehicles       – admin only
PUT  /api/vehicles/{id}  – admin only
DELETE /api/vehicles/{id} – admin only

All routes return 401 with no/invalid token and 403 for a non-admin user on
admin-only routes.
"""

import pytest

VALID_PASSWORD = "SecurePass123!"
VEHICLE_PAYLOAD = {
    "make": "Toyota",
    "model": "Camry",
    "category": "Sedan",
    "price": 25000.00,
    "quantity": 5,
}


# ---------------------------------------------------------------------------
# Helpers (not fixtures – just plain functions)
# ---------------------------------------------------------------------------


def _register(client, email: str, password: str = VALID_PASSWORD) -> dict:
    resp = client.post("/api/auth/register", json={"email": email, "password": password})
    assert resp.status_code == 201, resp.text
    return resp.json()


def _login(client, email: str, password: str = VALID_PASSWORD) -> str:
    resp = client.post("/api/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _promote_admin(db_session, email: str) -> None:
    from app.models import User, UserRole

    user = db_session.query(User).filter(User.email == email).first()
    assert user is not None, f"User {email!r} not found in DB"
    user.role = UserRole.ADMIN
    db_session.commit()


def _admin_token(client, db_session, email: str) -> str:
    _register(client, email)
    _promote_admin(db_session, email)
    return _login(client, email)


def _create_vehicle(client, token: str, payload: dict | None = None) -> dict:
    payload = payload or VEHICLE_PAYLOAD
    resp = client.post("/api/vehicles", json=payload, headers=_auth(token))
    assert resp.status_code == 201, resp.text
    return resp.json()


# ===========================================================================
# 401 – no / invalid token
# ===========================================================================


def test_list_vehicles_unauthenticated(client):
    resp = client.get("/api/vehicles")
    assert resp.status_code == 401


def test_create_vehicle_unauthenticated(client):
    resp = client.post("/api/vehicles", json=VEHICLE_PAYLOAD)
    assert resp.status_code == 401


def test_update_vehicle_unauthenticated(client):
    resp = client.put("/api/vehicles/1", json=VEHICLE_PAYLOAD)
    assert resp.status_code == 401


def test_delete_vehicle_unauthenticated(client):
    resp = client.delete("/api/vehicles/1")
    assert resp.status_code == 401


def test_invalid_bearer_token_returns_401(client):
    resp = client.get("/api/vehicles", headers={"Authorization": "Bearer not.a.real.jwt"})
    assert resp.status_code == 401


# ===========================================================================
# 403 – authenticated but not admin
# ===========================================================================


def test_create_vehicle_as_user_returns_403(client):
    _register(client, "user-create@example.com")
    token = _login(client, "user-create@example.com")
    resp = client.post("/api/vehicles", json=VEHICLE_PAYLOAD, headers=_auth(token))
    assert resp.status_code == 403


def test_update_vehicle_as_user_returns_403(client, db_session):
    admin_tok = _admin_token(client, db_session, "admin-upd-perm@example.com")
    v = _create_vehicle(client, admin_tok)

    _register(client, "user-upd-perm@example.com")
    user_tok = _login(client, "user-upd-perm@example.com")
    resp = client.put(f"/api/vehicles/{v['id']}", json=VEHICLE_PAYLOAD, headers=_auth(user_tok))
    assert resp.status_code == 403


def test_delete_vehicle_as_user_returns_403(client, db_session):
    admin_tok = _admin_token(client, db_session, "admin-del-perm@example.com")
    v = _create_vehicle(client, admin_tok)

    _register(client, "user-del-perm@example.com")
    user_tok = _login(client, "user-del-perm@example.com")
    resp = client.delete(f"/api/vehicles/{v['id']}", headers=_auth(user_tok))
    assert resp.status_code == 403


# ===========================================================================
# 422 – validation
# ===========================================================================


def test_create_vehicle_price_zero_returns_422(client, db_session):
    tok = _admin_token(client, db_session, "admin-val-p0@example.com")
    resp = client.post("/api/vehicles", json={**VEHICLE_PAYLOAD, "price": 0}, headers=_auth(tok))
    assert resp.status_code == 422


def test_create_vehicle_price_negative_returns_422(client, db_session):
    tok = _admin_token(client, db_session, "admin-val-pn@example.com")
    resp = client.post("/api/vehicles", json={**VEHICLE_PAYLOAD, "price": -1}, headers=_auth(tok))
    assert resp.status_code == 422


def test_create_vehicle_quantity_negative_returns_422(client, db_session):
    tok = _admin_token(client, db_session, "admin-val-qn@example.com")
    resp = client.post("/api/vehicles", json={**VEHICLE_PAYLOAD, "quantity": -1}, headers=_auth(tok))
    assert resp.status_code == 422


def test_create_vehicle_missing_make_returns_422(client, db_session):
    tok = _admin_token(client, db_session, "admin-val-mm@example.com")
    payload = {k: v for k, v in VEHICLE_PAYLOAD.items() if k != "make"}
    resp = client.post("/api/vehicles", json=payload, headers=_auth(tok))
    assert resp.status_code == 422


# ===========================================================================
# 200 / 201 / 204 – admin happy paths
# ===========================================================================


def test_create_vehicle_as_admin_returns_201(client, db_session):
    tok = _admin_token(client, db_session, "admin-create-ok@example.com")
    resp = client.post("/api/vehicles", json=VEHICLE_PAYLOAD, headers=_auth(tok))
    assert resp.status_code == 201
    body = resp.json()
    assert "id" in body
    assert body["make"] == "Toyota"
    assert body["model"] == "Camry"
    assert body["category"] == "Sedan"
    assert body["price"] == 25000.0
    assert body["quantity"] == 5


def test_list_vehicles_returns_all_including_out_of_stock(client, db_session):
    tok = _admin_token(client, db_session, "admin-list-ok@example.com")
    _create_vehicle(client, tok, {**VEHICLE_PAYLOAD, "quantity": 3})
    _create_vehicle(client, tok, {**VEHICLE_PAYLOAD, "model": "Corolla", "quantity": 0})

    resp = client.get("/api/vehicles", headers=_auth(tok))
    assert resp.status_code == 200
    vehicles = resp.json()
    assert len(vehicles) == 2
    quantities = {v["quantity"] for v in vehicles}
    assert 0 in quantities, "out-of-stock vehicle must appear in GET /api/vehicles"


def test_update_vehicle_as_admin_returns_200(client, db_session):
    tok = _admin_token(client, db_session, "admin-update-ok@example.com")
    v = _create_vehicle(client, tok)

    resp = client.put(
        f"/api/vehicles/{v['id']}",
        json={**VEHICLE_PAYLOAD, "price": 27500.0, "quantity": 10},
        headers=_auth(tok),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["price"] == 27500.0
    assert body["quantity"] == 10


def test_delete_vehicle_as_admin_returns_204(client, db_session):
    tok = _admin_token(client, db_session, "admin-delete-ok@example.com")
    v = _create_vehicle(client, tok)
    resp = client.delete(f"/api/vehicles/{v['id']}", headers=_auth(tok))
    assert resp.status_code == 204


# ===========================================================================
# 404 – missing ID
# ===========================================================================


def test_update_missing_vehicle_returns_404(client, db_session):
    tok = _admin_token(client, db_session, "admin-404u@example.com")
    resp = client.put("/api/vehicles/99999", json=VEHICLE_PAYLOAD, headers=_auth(tok))
    assert resp.status_code == 404


def test_delete_missing_vehicle_returns_404(client, db_session):
    tok = _admin_token(client, db_session, "admin-404d@example.com")
    resp = client.delete("/api/vehicles/99999", headers=_auth(tok))
    assert resp.status_code == 404
