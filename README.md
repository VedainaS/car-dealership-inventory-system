# Car Dealership Inventory System

Phase 1 delivers the FastAPI authentication backend with SQLite persistence. Vehicle inventory and the React frontend are planned for later phases.

## Requirements

- Python 3.11+
- Dependencies in `requirements.txt`

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
copy .env.example .env          # then edit secrets
```

Run the API:

```bash
cd backend
uvicorn app.main:app --reload
```

Health check: `GET /health`

## Authentication (Phase 1)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/auth/register` | Create a **user** account (email + password) |
| POST | `/api/auth/login` | Obtain a JWT bearer token |

Registration always creates accounts with the `user` role. Extra fields such as `role` in the JSON body are ignored.

### Bootstrap an admin account (local only)

Admin privileges are **not** selectable through the public register API. To promote an existing account locally:

1. Register via `POST /api/auth/register`.
2. From the `backend` directory (with the same `.env` / `DATABASE_URL` as the API):

```bash
python -m scripts.bootstrap_admin --email you@example.com
```

This CLI updates the database directly and is intended for development or controlled operations environments.

## Configuration

Environment variables (see `.env.example`):

- `DATABASE_URL` — development SQLite file
- `TEST_DATABASE_URL` — pytest-only SQLite file (isolated from dev data)
- `JWT_SECRET`, `JWT_ALGORITHM`, `JWT_EXPIRE_MINUTES`

## Tests

```bash
.venv\Scripts\python -m pytest -v
```

Pytest gives each test its own temporary SQLite file (via pytest's `tmp_path`) and overrides the app database session so development data is not touched. Optional `TEST_DATABASE_URL` in `.env` is for manual tooling only, not the test suite.
