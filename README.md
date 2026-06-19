# Mapah Hechsher Map

Mapah is a full-stack web app for discovering and moderating kosher place data.
Users can search places on a map, filter by hechsher and tags, submit new places or edits,
and track moderation status. Admins can review and approve/reject submissions.

## Current implementation snapshot

- Frontend: React + Vite + Mapbox GL (`mapah-frontend`)
- Backend: Flask + SQLAlchemy + Alembic + JWT cookie auth (`mapah-backend`)
- Database: PostgreSQL (default target)
- Moderation: Anthropic-based classification + deterministic safety checks
- Geocoding: Mapbox APIs

## Repository layout

- `mapah-backend` - Flask API, database models/migrations, moderation, tests
- `mapah-frontend` - React SPA, map UI, filters, auth, submissions, admin pages
- `spec.md` - product + technical spec aligned to implemented code
- `render.yaml` - backend Render blueprint
- `RENDER_DEPLOY.md` - deployment notes

## Implemented MVP capabilities

- Interactive Mapbox map with markers and popup actions
- Unified search (places + location suggestions)
- Viewport-based filtering by map bounds (`bbox`) plus hechsher and tags
- Place search by canonical name and saved aliases
- Clustered map markers with click-to-expand behavior
- JWT cookie auth with CSRF protection and refresh-token rotation
- User hechsher preferences and "My Submissions" page
- Dismissible in-app disclaimer banner about data accuracy
- Moderated submissions for:
  - new places
  - place edits
  - tag updates
  - alias updates
  - new hechsher creation (with icon upload)
- Admin moderation queue with approve/reject flows

## Quick start (local)

Run backend and frontend in separate terminals.

### 1) Backend

```powershell
Set-Location C:\Users\littl\PycharmProjects\Mapah-Hechsher-Map\mapah-backend
python -m pip install -r requirements.txt
python scripts/db_upgrade.py
python seed.py
python run.py
```

Backend defaults to `http://localhost:5000`.

### 2) Frontend

```powershell
Set-Location C:\Users\littl\PycharmProjects\Mapah-Hechsher-Map\mapah-frontend
npm install
npm run dev
```

Frontend defaults to `http://localhost:5173`.

Note: Vite proxy defaults to `http://localhost:5050` via `VITE_BACKEND_ORIGIN`.
If your backend is on `5000`, set `VITE_BACKEND_ORIGIN=http://localhost:5000`
or set backend `PORT=5050` before starting `run.py`.

## Environment variables (high-level)

### Backend (`mapah-backend`)

- `DATABASE_URL` (required in most setups)
- `SECRET_KEY`
- `JWT_SECRET_KEY`
- `CORS_ORIGINS`
- `MAPBOX_SECRET_TOKEN` (for server-side geocoding endpoint)
- `ANTHROPIC_API_KEY` (for live moderation)
- `HECHSHER_UPLOAD_DIR` (optional; defaults under `instance/uploads/hechshers`)

### Frontend (`mapah-frontend`)

- `VITE_MAPBOX_TOKEN` (required for map rendering)
- `VITE_API_BASE_URL` (optional; useful for deployed frontend/backend split)
- `VITE_BACKEND_ORIGIN` (optional; Vite dev proxy target)

## Testing

Backend tests:

```powershell
Set-Location C:\Users\littl\PycharmProjects\Mapah-Hechsher-Map\mapah-backend
python -m pytest -q
```

## Additional docs

- Backend details: `mapah-backend/README.md`
- Frontend details: `mapah-frontend/README.md`
- Deployment notes: `RENDER_DEPLOY.md`
- API contract reference: `mapah-backend/openapi.yaml`
