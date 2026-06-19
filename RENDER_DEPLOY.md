# Render Deploy Notes

This repo now includes a `render.yaml` blueprint that configures a backend persistent disk for hechsher icon uploads.

## What is configured

- Backend service: `mapah-backend`
- Persistent disk mount: `/var/data`
- Hechsher uploads directory: `/var/data/hechshers` (via `HECHSHER_UPLOAD_DIR`)
- Health check: `/api/csrf-token`

## First deploy (Blueprint)

1. In Render, choose **New +** -> **Blueprint**.
2. Connect this repository.
3. Confirm `render.yaml` is detected.
4. Add required environment variables (for example `DATABASE_URL`, `SECRET_KEY`, `JWT_SECRET_KEY`, `CORS_ORIGINS`, `MAPBOX_SECRET_TOKEN` if used).
5. Deploy.

## Frontend deploy (Static Site)

Create a separate Render **Static Site** for `mapah-frontend`.

- Root Directory: `mapah-frontend`
- Build Command: `npm install && npm run build`
- Publish Directory: `dist`
- Environment Variables:
  - `VITE_MAPBOX_TOKEN=<your mapbox public token>`
  - `VITE_API_BASE_URL=https://<your-backend-service>.onrender.com`

After first backend deploy, copy its public URL from Render and use that value for `VITE_API_BASE_URL`.

## If service already exists (manual update)

If you do not want to recreate via Blueprint, apply equivalent settings in the existing backend service:

- Add Persistent Disk:
  - Name: `mapah-data`
  - Mount Path: `/var/data`
  - Size: `1 GB` (increase if needed)
- Add env var:
  - `HECHSHER_UPLOAD_DIR=/var/data/hechshers`
- Redeploy.

## Verify persistence

1. Upload a hechsher icon from the app.
2. Open that icon URL directly.
3. Trigger a redeploy.
4. Open the same icon URL again; it should still load.

