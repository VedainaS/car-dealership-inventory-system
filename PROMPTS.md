# PROMPTS.md — Available AI conversation text

This file contains the exact prompt text drafted in ChatGPT and the Antigravity plan text pasted into the ChatGPT conversation. It is not a complete transcript. Missing chats are disclosed rather than reconstructed. Replace the final link marker with a public link to this ChatGPT conversation before submission, or paste its unedited transcript.

## Cursor (Phase 1)

The original Cursor chat history was deleted. The exact text pasted into Cursor cannot be independently verified. The following is the surviving Phase 1 prompt drafted in ChatGPT; it is included as a surviving source, not a reconstructed Cursor transcript.

~~~~text
Build Phase 1 of a Car Dealership Inventory System in this repository. Use Python FastAPI, a persistent SQLite database through SQLAlchemy, pytest, and a React/Vite frontend with Tailwind CSS. Start with the backend and authentication only. Do not implement vehicles or the frontend UI yet.

Follow genuine TDD: write meaningful failing tests first, run them and show the failure, commit the tests, implement the minimum code to pass, run the tests again, and commit the implementation. Use descriptive commit messages. This assignment requires an AI co-author trailer on every commit involving AI assistance: add two blank lines followed by `Co-authored-by: Cursor <AI@users.noreply.github.com>`.

Implement POST /api/auth/register and POST /api/auth/login with password hashing, JWT authentication, input validation, sensible HTTP errors, and tests for success, duplicate email, invalid input, and incorrect credentials. Registration must create ordinary users only; document a safe local method to bootstrap an admin account without allowing public users to choose the admin role. Keep secrets configurable through environment variables and include an example environment file. Use an on-disk test database isolated from development data.

Stop after Phase 1. Report the red and green test commands/results, files changed, and commit hashes. Do not claim a test or commit happened unless it actually did.
~~~~

The two existing Phase 1 test/implementation commits and the later bcrypt/database-isolation RED/GREEN commits preserve the work and co-author trailers. They do not replace the missing raw Cursor chat.

## Google Antigravity (Phase 2)

### Prompt 1 — Initial Phase 2 Request

```
Continue this existing Car Dealership Inventory System from its current Phase 1 state. First inspect the repository, README, tests, and Git history. Preserve the existing authentication implementation and commits. Do not create a new project or rewrite Git history.

Implement Phase 2: the protected vehicle and inventory REST API using FastAPI, SQLAlchemy, and the existing persistent SQLite setup.

Endpoints:
- POST /api/vehicles — admin only
- GET /api/vehicles — authenticated users
- GET /api/vehicles/search — authenticated users; combine optional case-insensitive make, model, and category filters with optional min_price and max_price
- PUT /api/vehicles/{id} — admin only
- DELETE /api/vehicles/{id} — admin only
- POST /api/vehicles/{id}/purchase — authenticated users; decrease stock by one
- POST /api/vehicles/{id}/restock — admin only; increase stock by a validated positive amount

Each vehicle needs a unique ID, make, model, category, positive price, and nonnegative integer quantity. Define and document whether GET /api/vehicles includes out-of-stock vehicles. Ensure /search does not get mistaken for an ID. Use appropriate 401, 403, 404, 409, and 422 responses. Verify JWT signatures and expiry, load the user from the database, and enforce admin permissions on the server. Ensure simultaneous purchases cannot make stock negative; use a database-safe conditional update and test the behavior.

Follow genuine TDD in small steps. Write meaningful tests first, run them to show expected failures, commit the tests, implement the behavior, run tests to green, and commit the implementation. Cover authentication, ordinary-user/admin permissions, validation, combined search, missing IDs, zero stock, purchase, restock, and concurrent purchase attempts. Preserve the existing 14 passing tests. Do not alter tests merely to make implementation pass.

This assignment requires an AI co-author trailer on each AI-assisted commit. Use two blank lines before: `Co-authored-by: Google Antigravity <AI@users.noreply.github.com>`. Update the README to record that both Cursor and Google Antigravity were used. Keep the raw, unedited text of this prompt and subsequent AI exchanges for the eventual root PROMPTS.md; do not substitute summaries for logs.

Stop when Phase 2 is complete. Report the exact red and green test commands and results, files changed, commit hashes, and any remaining limitations. Do not start the frontend.
```

### Response 1 — Plan text pasted into ChatGPT

~~~~text
The implementation plan is ready for your review. Here are the key design decisions I've made — please confirm before I begin coding:

### Key Decisions to Review

1. **`GET /api/vehicles` includes out-of-stock vehicles** (qty=0) — clients can show an "out of stock" label. A `?in_stock=true` filter can be added later if needed.
2. **`/search` route is declared before `/{id}`** — prevents FastAPI from trying to parse the string "search" as an integer vehicle ID.
3. **Concurrent purchase safety** — Uses a conditional `UPDATE vehicles SET quantity = quantity - 1 WHERE id = ? AND quantity > 0` and checks `rowcount`. If 0 rows updated → 409 Conflict. This is the correct SQLite-safe strategy (no `SELECT FOR UPDATE` in SQLite).
4. **Auth dependency** — A new `app/auth/dependencies.py` module decodes the JWT, verifies signature + expiry, and loads the User from the DB. `require_admin` raises 403 if the role is not admin.
5. **TDD order** — Two RED/GREEN commit pairs: first covers CRUD permissions/validation, second covers search + purchase/restock/concurrency.
6. **AI co-author trailer** on every AI-assisted commit with two blank lines before the `Co-authored-by:` line.

Does this plan look correct? Any changes before I proceed?

Phase 2: Vehicle Inventory REST API
Background
Phase 1 delivers a working FastAPI authentication backend with SQLite persistence. All 14 existing tests pass. This plan adds the protected vehicle/inventory REST API following genuine TDD: write failing tests → commit → implement → go green → commit.

Design Decisions
GET /api/vehicles — out-of-stock vehicles
Decision: include out-of-stock vehicles (quantity = 0). Rationale:

Clients need to know a model exists but is unavailable (show "out of stock" UI).
A separate filter parameter ?in_stock=true could be added later if needed.
/search follows the same inclusive rule.
Route ordering — /search vs /{id}
FastAPI matches routes in declaration order.
GET /api/vehicles/search will be declared before GET /api/vehicles/{id} so the literal path /search is never treated as an integer vehicle ID.

Concurrent purchase safety
SQLite doesn't support SELECT … FOR UPDATE. We'll use a conditional UPDATE with a WHERE quantity > 0 clause and check rowcount. If rowcount == 0 the stock was already 0 at commit time → 409 Conflict. This is the standard SQLite-safe approach; the test fires two near-simultaneous purchases against a vehicle with qty=1 and verifies exactly one succeeds.

TDD Steps (commit sequence)
Step	Description
1	test(vehicles): RED – authentication guard, CRUD permissions, validation
2	feat(vehicles): GREEN – Vehicle model, schemas, router, service
3	test(vehicles): RED – search, purchase, restock, concurrent purchase
4	feat(vehicles): GREEN – search, purchase/restock with stock safety
5	docs: Update README + PROMPTS.md
Proposed Changes
Database / Models
[MODIFY] 
models.py
Add Vehicle ORM model with columns: id, make, model, category, price (Numeric), quantity (Integer ≥ 0).
Schemas
[MODIFY] 
schemas.py
Add VehicleCreate, VehicleUpdate, VehiclePublic, RestockRequest Pydantic models.
price validated > 0; quantity validated >= 0; restock amount validated > 0.
Auth — dependency helpers
[NEW] 
backend/app/auth/dependencies.py
get_current_user(token, db) — decode JWT, verify signature + expiry, load User from DB → 401 if invalid.
require_admin(current_user) — raises 403 if role ≠ admin.
Vehicle feature
[NEW] 
backend/app/vehicles/
__init__.py
service.py — pure DB logic (create, list, search, get_by_id, update, delete, purchase, restock).
router.py — 7 endpoints wired to service; HTTP error translation.
Main
[MODIFY] 
main.py
Include vehicles_router from app.vehicles.router.
Tests
[NEW] 
backend/tests/test_vehicles_crud.py
Tests for: auth guard (no token → 401), ordinary-user permission (→ 403 on admin routes), validation (bad price, bad qty, missing fields → 422), create/read/update/delete happy paths, missing ID (→ 404), duplicate-guard (no unique constraint beyond id, so N/A here).

[NEW] 
backend/tests/test_vehicles_search.py
Tests for: combined make+model+category filter (case-insensitive), min_price/max_price, /search not treated as an integer ID, empty result set.

[NEW] 
backend/tests/test_vehicles_inventory.py
Tests for: purchase happy path (qty decrements), purchase on zero stock (→ 409), restock happy path (qty increments), restock with non-positive amount (→ 422), concurrent purchase (two threads, one must get 409).

Documentation
[MODIFY] 
README.md
Add Phase 2 section with endpoint table.
Record both Cursor and Google Antigravity as AI co-authors.
[NEW] 
PROMPTS.md
Raw, unedited text of the Phase 2 prompt and subsequent AI exchanges.
Verification Plan
Automated Tests

# Baseline (must still be 14 passed):
.venv\Scripts\python -m pytest -v
# After RED commits — confirm new tests fail with expected errors.
# After GREEN commits — confirm full suite passes (14 + new tests).
Manual Verification
Run server: cd backend && uvicorn app.main:app --reload
Confirm /health still responds 200.
Optionally curl the new endpoints with a bearer token.
~~~~

### Prompt 2 — Plan Approval with Three Adjustments

```
Plan approved with three adjustments:

1. A failed conditional purchase UPDATE cannot by itself distinguish a missing vehicle from an out-of-stock vehicle. Return 404 for a missing ID and 409 for an existing vehicle with zero stock.
2. The concurrency test must use independent database sessions/connections. Review the current on-disk test fixture’s StaticPool setup so the test actually exercises concurrent transactions rather than sharing one connection.
3. Do not invent earlier raw AI chat logs for PROMPTS.md. Include only verbatim prompts/exchanges you have access to, and leave a clearly marked place for me to add any missing Cursor history.

GET /api/vehicles should include out-of-stock vehicles as proposed. The conditional UPDATE approach is appropriate. There is no GET /api/vehicles/{id} in the requested API, so route-order handling matters only if you add that route.

Please begin the RED/GREEN implementation and show the actual test output and commits at each checkpoint.
```

### Response after Prompt 2

No Antigravity response was received after Prompt 2 because the plan ended. The generated files and the RED commit are preserved in the repository. There is no response transcript for this step.

## ChatGPT review and implementation

[ADD PUBLIC LINK TO THIS CHATGPT CONVERSATION OR PASTE THE COMPLETE UNEDITED CHAT LOG HERE]
