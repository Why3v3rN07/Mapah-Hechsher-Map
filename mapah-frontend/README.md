## Note that this readme is outdated. Refer to spec.md for better info.


# Mapah Frontend

React + Vite frontend for Mapah MVP.

## Setup

1. Copy `.env.example` to `.env` and set `VITE_MAPBOX_TOKEN`.
2. Install dependencies.
3. Run dev server.

```powershell
npm install
npm run dev
```

Frontend runs on `http://localhost:5173` and proxies `/api` + `/auth` to backend `http://localhost:5000`.

## Build

```powershell
npm run build
npm run preview
```

## Main folders

- `src/components/Map` – map rendering + marker popups
- `src/components/Filters` – search/filter controls
- `src/components/Auth` – login/register modal
- `src/components/Submission` – add/edit/tag modal
- `src/components/Admin` – admin moderation queue UI
- `src/components/MySubmissions` – user upload status UI
- `src/api` – API client modules
- `src/contexts` – auth/filter state
