# Mapah Frontend

React + Vite SPA for the Mapah MVP.

## What it currently includes

- Mapbox map with marker popups and quick actions (tag/edit)
- Unified search dropdown (place results + location suggestions)
- Filters for hechshers, tags, and proximity radius (`mi`/`km`)
- Auth modal (register/login/logout) with cookie-based session flow
- Submission modal for:
  - `new_place`
  - `edit`
  - `tag_update`
  - inline creation of new hechshers (with optional icon upload)
- Preferences page for saved hechshers
- My Submissions page
- Admin queue page (approve/reject)

## Setup

Install and run:

```powershell
Set-Location C:\Users\littl\PycharmProjects\Mapah-Hechsher-Map\mapah-frontend
npm install
npm run dev
```

Vite dev server defaults to `http://localhost:5173`.

## Environment variables

There is no committed `.env.example` in this repo.

- `VITE_MAPBOX_TOKEN` (required for map rendering)
- `VITE_API_BASE_URL` (optional; use when frontend and backend are on different origins)
- `VITE_BACKEND_ORIGIN` (optional; Vite proxy target, defaults to `http://localhost:5050`)

Proxy routes in `vite.config.js`:

- `/api`
- `/auth`
- `/instance`

If backend runs on `http://localhost:5000`, set `VITE_BACKEND_ORIGIN=http://localhost:5000`
or run backend on port `5050`.

## Build

```powershell
npm run build
npm run preview
```

## Scripts

- `npm run dev` - start Vite dev server
- `npm run build` - production build
- `npm run preview` - preview production build
- `npm run lint` - run ESLint

## Key folders

- `src/components/Map` - map rendering and marker popup interactions
- `src/components/Filters` - unified search and filter controls
- `src/components/Auth` - authentication modal UI
- `src/components/Submission` - submission/edit/tag modal UI
- `src/components/Admin` - admin moderation queue UI
- `src/components/MySubmissions` - user submission history UI
- `src/pages` - route-level pages (`Home`, `Preferences`, `My Submissions`, `Admin`)
- `src/api` - API clients (`axios` + CSRF + refresh handling)
- `src/contexts` - shared auth and filter state
