"""Phase 2 – Vehicle inventory: purchase, restock, and concurrent purchase safety.

Design contract
---------------
POST /api/vehicles/{id}/purchase  – authenticated (any role)
  - 200 + updated vehicle on success (quantity decremented by 1)
  - 401 if not authenticated
  - 404 if vehicle does not exist
  - 409 if vehicle exists but quantity == 0

POST /api/vehicles/{id}/restock   – admin only
  - 200 + updated vehicle on success (quantity += amount)
  - 401 if not authenticated
  - 403 if not admin
  - 404 if vehicle does not exist
  - 422 if amount is 0 or negative

Concurrent-purchase safety
---------------------------
The service uses a conditional UPDATE:

    UPDATE vehicles
    SET quantity = quantity - 1
    WHERE id = ? AND quantity > 0

and checks rowcount.  If rowcount == 0, the vehicle exists but was out of
stock at commit time → 409.  This prevents stock from going negative even
when two transactions race.

The concurrent_client fixture (see conftest.py) uses NullPool so each request
opens its own SQLite connection.  WAL journal mode lets both connections
proceed without an immediate exclusive lock.  SQLite still serialises the
final commit, so one UPDATE sees quantity > 0 and succeeds; the other sees
quantity == 0 and is rejected with 409.
"""

import threading

import pytest

VALID_PASSWORD = "SecurePass123!"
VEHICLE = {"make": "Toyota", "model": "Camry", "category": "Sedan", "price": 25000.0, "quantity": 5}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _register(client, email: str) -> None:
    r = client.post("/api/auth/register", json={"email": email, "password": VALID_PASSWORD})
    assert r.status_code == 201, r.text


def _login(client, email: str) -> str:
    r = client.post("/api/auth/login", json={"email": email, "password": VALID_PASSWORD})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _promote_admin(db_session, email: str) -> None:
    from app.models import User, UserRole

    user = db_session.query(User).filter(User.email == email).first()
    assert user is not None
    user.role = UserRole.ADMIN
    db_session.commit()


def _setup_admin_and_vehicle(client, db_session, admin_email: str, quantity: int = 5) -> tuple[str, dict]:
    """Register + promote admin, create vehicle, return (admin_token, vehicle_body)."""
    _register(client, admin_email)
    _promote_admin(db_session, admin_email)
    tok = _login(client, admin_email)
    r = client.post("/api/vehicles", json={**VEHICLE, "quantity": quantity}, headers=_auth(tok))
    assert r.status_code == 201, r.text
    return tok, r.json()


# ===========================================================================
# Purchase – auth guard
# ===========================================================================


def test_purchase_unauthenticated_returns_401(client):
    resp = client.post("/api/vehicles/1/purchase")
    assert resp.status_code == 401


# ===========================================================================
# Purchase – happy path
# ===========================================================================


def test_purchase_decrements_quantity_by_one(client, db_session):
    admin_tok, v = _setup_admin_and_vehicle(client, db_session, "admin-pur-ok@example.com", quantity=3)
    _register(client, "buyer-pur-ok@example.com")
    buyer_tok = _login(client, "buyer-pur-ok@example.com")

    resp = client.post(f"/api/vehicles/{v['id']}/purchase", headers=_auth(buyer_tok))
    assert resp.status_code == 200
    assert resp.json()["quantity"] == 2


def test_admin_can_also_purchase(client, db_session):
    admin_tok, v = _setup_admin_and_vehicle(client, db_session, "admin-pur-self@example.com", quantity=2)

    resp = client.post(f"/api/vehicles/{v['id']}/purchase", headers=_auth(admin_tok))
    assert resp.status_code == 200
    assert resp.json()["quantity"] == 1


# ===========================================================================
# Purchase – 404 (vehicle does not exist)
# ===========================================================================


def test_purchase_missing_vehicle_returns_404(client, db_session):
    _register(client, "buyer-pur-404@example.com")
    buyer_tok = _login(client, "buyer-pur-404@example.com")

    resp = client.post("/api/vehicles/99999/purchase", headers=_auth(buyer_tok))
    assert resp.status_code == 404


# ===========================================================================
# Purchase – 409 (out of stock)
# ===========================================================================


def test_purchase_out_of_stock_returns_409(client, db_session):
    admin_tok, v = _setup_admin_and_vehicle(client, db_session, "admin-pur-oos@example.com", quantity=0)
    _register(client, "buyer-pur-oos@example.com")
    buyer_tok = _login(client, "buyer-pur-oos@example.com")

    resp = client.post(f"/api/vehicles/{v['id']}/purchase", headers=_auth(buyer_tok))
    assert resp.status_code == 409


def test_purchase_after_last_unit_returns_409(client, db_session):
    """Buy the last unit; the next purchase must see 409, not 200."""
    admin_tok, v = _setup_admin_and_vehicle(client, db_session, "admin-pur-last@example.com", quantity=1)
    _register(client, "buyer-pur-last@example.com")
    buyer_tok = _login(client, "buyer-pur-last@example.com")

    first = client.post(f"/api/vehicles/{v['id']}/purchase", headers=_auth(buyer_tok))
    assert first.status_code == 200
    assert first.json()["quantity"] == 0

    second = client.post(f"/api/vehicles/{v['id']}/purchase", headers=_auth(buyer_tok))
    assert second.status_code == 409


# ===========================================================================
# Restock – auth guard and role enforcement
# ===========================================================================


def test_restock_unauthenticated_returns_401(client):
    resp = client.post("/api/vehicles/1/restock", json={"amount": 5})
    assert resp.status_code == 401


def test_restock_as_user_returns_403(client, db_session):
    admin_tok, v = _setup_admin_and_vehicle(client, db_session, "admin-rst-403@example.com")
    _register(client, "user-rst-403@example.com")
    user_tok = _login(client, "user-rst-403@example.com")

    resp = client.post(f"/api/vehicles/{v['id']}/restock", json={"amount": 10}, headers=_auth(user_tok))
    assert resp.status_code == 403


# ===========================================================================
# Restock – happy path
# ===========================================================================


def test_restock_increases_quantity(client, db_session):
    admin_tok, v = _setup_admin_and_vehicle(client, db_session, "admin-rst-ok@example.com", quantity=2)

    resp = client.post(f"/api/vehicles/{v['id']}/restock", json={"amount": 8}, headers=_auth(admin_tok))
    assert resp.status_code == 200
    assert resp.json()["quantity"] == 10


# ===========================================================================
# Restock – 422 (invalid amount)
# ===========================================================================


def test_restock_amount_zero_returns_422(client, db_session):
    admin_tok, v = _setup_admin_and_vehicle(client, db_session, "admin-rst-z@example.com")
    resp = client.post(f"/api/vehicles/{v['id']}/restock", json={"amount": 0}, headers=_auth(admin_tok))
    assert resp.status_code == 422


def test_restock_amount_negative_returns_422(client, db_session):
    admin_tok, v = _setup_admin_and_vehicle(client, db_session, "admin-rst-neg@example.com")
    resp = client.post(f"/api/vehicles/{v['id']}/restock", json={"amount": -5}, headers=_auth(admin_tok))
    assert resp.status_code == 422


# ===========================================================================
# Restock – 404
# ===========================================================================


def test_restock_missing_vehicle_returns_404(client, db_session):
    admin_tok, _ = _setup_admin_and_vehicle(client, db_session, "admin-rst-404@example.com")
    resp = client.post("/api/vehicles/99999/restock", json={"amount": 5}, headers=_auth(admin_tok))
    assert resp.status_code == 404


# ===========================================================================
# Concurrent purchase – stock cannot go negative
#
# Strategy
# --------
# Two threads each call POST /api/vehicles/{id}/purchase through the same
# TestClient.  The concurrent_client fixture uses NullPool so each request
# gets its own SQLite connection (independent transactions).  WAL mode lets
# both connections start their write transactions before the first commits.
#
# The service executes:
#   UPDATE vehicles SET quantity = quantity - 1
#   WHERE id = ? AND quantity > 0
# and checks rowcount.  SQLite serialises the actual commits, so:
#   - First committer: rowcount == 1 → 200
#   - Second committer: rowcount == 0 (qty already 0) → 409
# This guarantees exactly one success and stock never goes below zero.
# ===========================================================================


def test_concurrent_purchase_only_one_succeeds(concurrent_client, concurrent_db_session):
    """Two simultaneous purchases of the last unit: exactly one 200, one 409."""
    # --- setup ---
    admin_email = "admin-concurrent@example.com"
    buyer_email = "buyer-concurrent@example.com"
    _register(concurrent_client, admin_email)
    _promote_admin(concurrent_db_session, admin_email)
    admin_tok = _login(concurrent_client, admin_email)

    # Vehicle with exactly 1 unit in stock
    r = concurrent_client.post(
        "/api/vehicles",
        json={**VEHICLE, "quantity": 1},
        headers=_auth(admin_tok),
    )
    assert r.status_code == 201, r.text
    vehicle_id = r.json()["id"]

    _register(concurrent_client, buyer_email)
    buyer_tok = _login(concurrent_client, buyer_email)

    # --- concurrent purchases ---
    results: list[int] = []
    lock = threading.Lock()

    def do_purchase() -> None:
        resp = concurrent_client.post(
            f"/api/vehicles/{vehicle_id}/purchase",
            headers=_auth(buyer_tok),
        )
        with lock:
            results.append(resp.status_code)

    t1 = threading.Thread(target=do_purchase)
    t2 = threading.Thread(target=do_purchase)
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    assert sorted(results) == [200, 409], (
        f"Expected exactly one 200 and one 409 from concurrent purchases; got {results}"
    )

    # Verify stock is 0 and never went below
    vehicles = concurrent_client.get("/api/vehicles", headers=_auth(buyer_tok)).json()
    vehicle = next(v for v in vehicles if v["id"] == vehicle_id)
    assert vehicle["quantity"] == 0, "Stock must be 0 after one successful purchase from 1"
