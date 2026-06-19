# Mapah Backend

Flask API for the Mapah MVP.

It provides:

- cookie-based JWT auth (`/auth/*`) with refresh rotation + CSRF double-submit
- map/search APIs (`/api/places`, `/api/locations/search`, `/api/hechshers*`)
- moderated submission pipeline (`new_place`, `edit`, `tag_update`, `alias_update`, `hechsher_create`)
- admin moderation queue (`/api/admin/submissions*`)

## Stack

- Flask 3
- Flask-SQLAlchemy + Flask-Migrate (Alembic)
- Flask-JWT-Extended
- Flask-Limiter
- PostgreSQL (default)
- Anthropic SDK (moderation)
- `requests` (Mapbox geocoding)

## Setup

Install dependencies:

```powershell
Set-Location C:\Users\littl\PycharmProjects\Mapah-Hechsher-Map\mapah-backend
python -m pip install -r requirements.txt
```

Configure environment variables (there is no committed `.env.example` in this repo).

Minimum practical vars for local development:

- `DATABASE_URL`
- `SECRET_KEY`
- `JWT_SECRET_KEY`

Common optional vars:

- `CORS_ORIGINS`
- `MAPBOX_SECRET_TOKEN`
- `ANTHROPIC_API_KEY`
- `HECHSHER_UPLOAD_DIR`
- `PORT` (defaults to `5000`)

## Database migrations

Run safe upgrade helper:

```powershell
python scripts/db_upgrade.py
```

PowerShell wrapper:

```powershell
.\scripts\db_upgrade.ps1
```

Upgrade and reseed from scratch:

```powershell
python scripts/db_upgrade.py --seed --wipe
```

## Seed data

`seed.py` can populate users, hechshers, places, preferences, and submission history.

Run:

```powershell
python seed.py
```

Wipe and reseed:

```powershell
python seed.py --wipe
```

Auto-upgrade then wipe+seed:

```powershell
python seed.py --auto-upgrade --wipe
```

Default seeded users:

- `admin@mapah.local` / `AdminPass123!`
- `yael@mapah.local` / `YaelPass123!`
- `david@mapah.local` / `DavidPass123!`
- `sarah@mapah.local` / `SarahPass123!`
- `moshe@mapah.local` / `MoshePass123!`

## Run

```powershell
python run.py
```

Defaults:

- host: `0.0.0.0`
- port: `5000` (or `PORT` / `FLASK_RUN_PORT`)

## Moderation behavior

- Uses Anthropic via `app/services/moderation.py`
- Adds deterministic anti-spam heuristics and consistency checks
- Missing `ANTHROPIC_API_KEY`:
  - in tests (or with `ANTHROPIC_AUTO_APPROVE_WITHOUT_KEY=true`): auto-approve
  - otherwise: fail-closed to `flagged`
- Supports model fallback chain via `ANTHROPIC_MODERATION_FALLBACK_MODELS`

## API groups

- Public:
  - `GET /api/csrf-token`
  - `GET /api/places`
  - `GET /api/locations/search`
  - `GET /api/hechshers`
  - `GET /api/hechshers/search`
  - `POST /api/submissions/place`
  - `POST /api/places/{id}/tags`
  - `GET /api/places/{id}/aliases`
  - `POST /api/places/{id}/aliases` (auth required)
  - `POST /api/hechshers`
- Auth:
  - `POST /auth/register`, `POST /auth/login`, `POST /auth/refresh`, `POST /auth/logout`
  - `POST /auth/change-password`, `DELETE /auth/account`
- User:
  - `GET/PUT /api/me/preferences/hechshers`
  - `GET /api/me/submissions`
- Admin:
  - `GET /api/admin/submissions`
  - `GET /api/admin/submissions/{id}`
  - `POST /api/admin/submissions/{id}/approve`
  - `POST /api/admin/submissions/{id}/reject`

## Tests

```powershell
python -m pytest -q
```

Current test files:

- `tests/test_app_smoke.py`
- `tests/test_e2e_happy_path.py`
- `tests/test_spec_gap_fixes.py`
- `tests/test_submission_moderation.py`

## Key paths

- `app/__init__.py` - app factory, CORS, JWT callbacks, blueprints
- `app/models.py` - SQLAlchemy models/enums
- `app/auth/views.py` - auth/session routes
- `app/api/` - places, hechshers, submissions, me, admin
- `app/services/geocoding.py` - Mapbox geocoding helpers
- `app/services/moderation.py` - moderation integration and heuristics
- `migrations/versions/` - Alembic revisions
- `openapi.yaml` - API contract document
