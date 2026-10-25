"""Phase 2 – Vehicle search: combined filters, case-insensitivity, price range.

Design contract
---------------
GET /api/vehicles/search
  Query params (all optional):
    make       – exact case-insensitive match
    model      – exact case-insensitive match
    category   – exact case-insensitive match
    min_price  – inclusive lower bound on price
    max_price  – inclusive upper bound on price

Returns a JSON array (possibly empty).
Route is declared before /{id} so the literal string "search" is never
mistaken for an integer vehicle ID – confirmed by the 401/200 assertions
below (not 422 Unprocessable Entity).
"""

VALID_PASSWORD = "SecurePass123!"

FLEET = [
    {"make": "Toyota", "model": "Camry", "category": "Sedan", "price": 25000.0, "quantity": 5},
    {"make": "Toyota", "model": "RAV4", "category": "SUV", "price": 32000.0, "quantity": 3},
    {"make": "Honda", "model": "Civic", "category": "Sedan", "price": 21000.0, "quantity": 8},
    {"make": "Honda", "model": "CR-V", "category": "SUV", "price": 30000.0, "quantity": 2},
    {"make": "Ford", "model": "F-150", "category": "Truck", "price": 45000.0, "quantity": 1},
]


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

    # The auth service normalises emails to lowercase before storing them.
    user = db_session.query(User).filter(User.email == email.lower()).first()
    assert user is not None, f"User {email!r} not found in DB (looked up as {email.lower()!r})"
    user.role = UserRole.ADMIN
    db_session.commit()



def _seed_fleet(client, admin_tok: str) -> None:
    for v in FLEET:
        r = client.post("/api/vehicles", json=v, headers=_auth(admin_tok))
        assert r.status_code == 201, r.text


def _search(client, token: str, **params) -> list:
    resp = client.get("/api/vehicles/search", params=params, headers=_auth(token))
    assert resp.status_code == 200, resp.text
    return resp.json()


# ===========================================================================
# Route is not treated as an integer ID
# ===========================================================================


def test_search_without_token_returns_401_not_422(client):
    """The /search path must not be parsed as an integer vehicle ID (which would 422)."""
    resp = client.get("/api/vehicles/search")
    assert resp.status_code == 401


def test_search_with_valid_token_returns_200(client, db_session):
    _register(client, "user-search-basic@example.com")
    tok = _login(client, "user-search-basic@example.com")
    resp = client.get("/api/vehicles/search", headers=_auth(tok))
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


# ===========================================================================
# Filter: make (case-insensitive)
# ===========================================================================


def test_search_make_case_insensitive(client, db_session):
    _register(client, "admin-srch-make@example.com")
    _promote_admin(db_session, "admin-srch-make@example.com")
    admin_tok = _login(client, "admin-srch-make@example.com")
    _seed_fleet(client, admin_tok)

    # lower-case query should match "Toyota" (stored with capital T)
    results = _search(client, admin_tok, make="toyota")
    assert len(results) == 2
    assert all(v["make"] == "Toyota" for v in results)


def test_search_make_treats_sql_wildcards_as_literal_text(client, db_session):
    _register(client, "admin-srch-literal@example.com")
    _promote_admin(db_session, "admin-srch-literal@example.com")
    admin_tok = _login(client, "admin-srch-literal@example.com")
    _seed_fleet(client, admin_tok)

    assert _search(client, admin_tok, make="%") == []
    assert _search(client, admin_tok, make="Toy_ta") == []


def test_search_make_uppercase_also_matches(client, db_session):
    _register(client, "admin-srch-makeU@example.com")
    _promote_admin(db_session, "admin-srch-makeU@example.com")
    admin_tok = _login(client, "admin-srch-makeU@example.com")
    _seed_fleet(client, admin_tok)

    results = _search(client, admin_tok, make="HONDA")
    assert len(results) == 2
    assert all(v["make"] == "Honda" for v in results)


# ===========================================================================
# Filter: model
# ===========================================================================


def test_search_model_filter(client, db_session):
    _register(client, "admin-srch-model@example.com")
    _promote_admin(db_session, "admin-srch-model@example.com")
    admin_tok = _login(client, "admin-srch-model@example.com")
    _seed_fleet(client, admin_tok)

    results = _search(client, admin_tok, model="civic")
    assert len(results) == 1
    assert results[0]["model"] == "Civic"


# ===========================================================================
# Filter: category
# ===========================================================================


def test_search_category_filter(client, db_session):
    _register(client, "admin-srch-cat@example.com")
    _promote_admin(db_session, "admin-srch-cat@example.com")
    admin_tok = _login(client, "admin-srch-cat@example.com")
    _seed_fleet(client, admin_tok)

    results = _search(client, admin_tok, category="SUV")
    assert len(results) == 2
    assert all(v["category"] == "SUV" for v in results)


# ===========================================================================
# Combined filters
# ===========================================================================


def test_search_make_and_category_combined(client, db_session):
    _register(client, "admin-srch-combo@example.com")
    _promote_admin(db_session, "admin-srch-combo@example.com")
    admin_tok = _login(client, "admin-srch-combo@example.com")
    _seed_fleet(client, admin_tok)

    # Toyota + SUV → only RAV4
    results = _search(client, admin_tok, make="toyota", category="suv")
    assert len(results) == 1
    assert results[0]["model"] == "RAV4"


def test_search_no_match_returns_empty_list(client, db_session):
    _register(client, "admin-srch-empty@example.com")
    _promote_admin(db_session, "admin-srch-empty@example.com")
    admin_tok = _login(client, "admin-srch-empty@example.com")
    _seed_fleet(client, admin_tok)

    results = _search(client, admin_tok, make="Lamborghini")
    assert results == []


# ===========================================================================
# Filter: price range
# ===========================================================================


def test_search_min_price(client, db_session):
    _register(client, "admin-srch-minp@example.com")
    _promote_admin(db_session, "admin-srch-minp@example.com")
    admin_tok = _login(client, "admin-srch-minp@example.com")
    _seed_fleet(client, admin_tok)

    # min_price=40000 → only Ford F-150 at 45000
    results = _search(client, admin_tok, min_price=40000)
    assert len(results) == 1
    assert results[0]["model"] == "F-150"


def test_search_max_price(client, db_session):
    _register(client, "admin-srch-maxp@example.com")
    _promote_admin(db_session, "admin-srch-maxp@example.com")
    admin_tok = _login(client, "admin-srch-maxp@example.com")
    _seed_fleet(client, admin_tok)

    # max_price=22000 → only Honda Civic at 21000
    results = _search(client, admin_tok, max_price=22000)
    assert len(results) == 1
    assert results[0]["model"] == "Civic"


def test_search_price_range(client, db_session):
    _register(client, "admin-srch-range@example.com")
    _promote_admin(db_session, "admin-srch-range@example.com")
    admin_tok = _login(client, "admin-srch-range@example.com")
    _seed_fleet(client, admin_tok)

    # 25000–32000 → Camry (25000), RAV4 (32000), CR-V (30000)
    results = _search(client, admin_tok, min_price=25000, max_price=32000)
    models = {v["model"] for v in results}
    assert models == {"Camry", "RAV4", "CR-V"}
