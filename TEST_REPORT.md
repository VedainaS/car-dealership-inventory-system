# Test report

Verified on 24 October 2026 against the project snapshot in this repository.

| Check | Command | Result |
|---|---|---|
| Phase 2 RED checkpoint | `python -m pytest -q` on commit `0d8721a` | **39 failed, 17 passed**; vehicle routes did not exist yet |
| Exact-search regression RED | `python -m pytest -q backend/tests/test_vehicles_search.py::test_search_make_treats_sql_wildcards_as_literal_text` before changing the query | **1 failed**; `make=%` matched all five seeded vehicles |
| SPA integration RED | `python -m pytest -q backend/tests/test_frontend_integration.py` before adding `/me` and CORS | **3 failed**; two 404s and a 405 |
| Frontend RED checkpoint | `npm test -- --reporter=dot` before creating `src/App.jsx` | **1 test suite failed at collection** because the app module did not yet exist |
| Full backend suite | `python -m pytest -q` | **60 passed, 1 warning, 26.92 s** |
| Frontend suite | `npm test -- --reporter=dot` | **9 passed, 1 file, 2.26 s** |
| Production build | `npm run build` | **Passed**; Vite built 1,581 modules in 2.16 s |

The backend warning was a Starlette `httpx` deprecation warning from its test client. It did not fail a test. The screenshots in `frontend/screenshots/` were captured from the live SPA connected to a seeded local API; the sample database is not shipped.

The tests cover registration, login, bcrypt's 72-byte limit, JWT/roles, protected CRUD, search, validation, zero stock, restock, simultaneous last-unit purchases, CORS, account identification, SPA auth, filters, purchasing, and admin workflows. They do not replace a payment or production load test; purchase only changes inventory quantity.
