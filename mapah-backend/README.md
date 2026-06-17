# Mapah Backend

Flask API for Mapah MVP (JWT auth, moderation pipeline, submissions, admin queue).

## Setup

1. Copy `.env.example` to `.env` and fill required values.
2. Install dependencies.

```powershell
python -m pip install -r requirements.txt
```

## Migrations + Upgrade Script

Run Alembic upgrade safely (with schema verification + recovery):

```powershell
python scripts/db_upgrade.py
```

PowerShell wrapper:

```powershell
./scripts/db_upgrade.ps1
```

Upgrade + reseed from scratch:

```powershell
python scripts/db_upgrade.py --seed --wipe
```

## Seed Data

The seed script creates:
- admin + basic users
- hechshers + aliases
- sample places + tags + place-hechsher links
- user preferred hechshers
- sample submission moderation history

Run without wipe:

```powershell
python seed.py
```

Run with wipe:

```powershell
python seed.py --wipe
```

Run with automatic migration upgrade first:

```powershell
python seed.py --auto-upgrade --wipe
```

## Tests

Smoke + E2E happy-path tests:

```powershell
python -m pytest -q
```

The E2E test file is `tests/test_e2e_happy_path.py` and covers:
1. register
2. login
3. submit new place
4. admin queue fetch
5. admin approval

## Run Server

```powershell
python run.py
```

Server default: `http://localhost:5000`

## Key files

- `app/__init__.py` - app factory + extensions + JWT callbacks
- `app/models.py` - target MVP data model
- `app/auth/views.py` - auth/session endpoints
- `app/api/` - public/auth/admin API routes
- `migrations/` - Alembic migration history
- `scripts/db_upgrade.py` - migration/upgrade helper
- `openapi.yaml` - OpenAPI 3.1 contract
