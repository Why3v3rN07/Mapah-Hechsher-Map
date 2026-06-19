# Mapah Product + Technical Spec (Spec-Driven Development)

_Last updated from implemented codebase on 2026-06-17._

## 1) Purpose
Mapah helps users find nearby places to eat based on kosher certifications (hechshers) they follow.

This spec is the source of truth for implementation planning and acceptance.

## 2) Scope and Phases

### MVP (In Scope)
- View a Mapbox map with place markers showing hechsher symbols as icons.
- Map defaults to Jerusalem (31.7683°N, 35.2137°E) if location services unavailable.
- Click on map location to center and zoom; map interaction includes marker clicking.
- Unified search dropdown combines place results and typed-location suggestions.
- Search/filter places by:
  - hechsher (searchable dropdown with icon + alias matching, multi-select)
  - place name
  - place tags
  - proximity radius from map center or typed location
- Reset Filters button to clear all active filters including hechshers.
- Account system with JWT auth.
- Logged-in users can save preferred hechshers via dedicated preferences page.
- Map defaults:
  - logged-in + preferences exist: show places matching preferred hechshers
  - otherwise: show all places
- Add place manually with required fields: name, address (with typeahead), hechsher (searchable, with "Add New Hechsher" button for new hechsher creation), tags.
- Add new hechsher via modal form with fields: display name, aliases, icon upload.
- Add place with location detection for address/coordinates.
- Tag existing places (anonymous allowed).
- Add aliases to existing places (authenticated only); alias additions pass through moderation.
- Edit existing places via the same moderated submission pipeline (`submission_type=edit`; login required).
- Submission form includes close button (X) to dismiss without saving.
- API submission rate limit counts only successful submissions; failed submissions do not increment counter.
- AI spam moderation is implemented via a direct Anthropic API call with structured JSON output (no LangChain/agent orchestration in MVP).
- Admin queue UI in frontend with separate sections for flagged vs non-flagged; admin-only access.
- Admin view shows human-readable submission summaries (not raw JSON).
- Non-flagged submissions appear immediately on map.
- Logged-in users can view upload status for their own submissions on dedicated "My Submissions" page with human-readable display.
- Typed location search/geocoding uses Mapbox geocoding APIs.
- Address field in submission form uses geocoding typeahead; valid address selection required.
- CSRF bootstrap endpoint is implemented at `GET /api/csrf-token`.
- Location suggestion endpoint is implemented at `GET /api/locations/search`.
- Submission anti-abuse: max one successful submission per minute per user (or per anonymous client key).

### Future (Out of MVP)
- Certificate OCR.
- Expanded verification levels/business logic (field exists; keep schema support).

## 3) Current Stack Baseline (from codebase)

### Frontend
- React + Vite (`mapah-frontend`)
- `mapbox-gl`
- `axios`
- `react-router-dom`
- ESLint
- API client includes local-dev backend fallback bases (`localhost:5050`, `localhost:5000`, `localhost:8000`) when proxy routing is unavailable.

### Backend
- Flask app factory (`mapah-backend/app/__init__.py`)
- Flask-SQLAlchemy + Flask-Migrate
- Flask-JWT-Extended (JWT cookies)
- Flask-Limiter (submission anti-abuse)
- Anthropic SDK integration for moderation
- `requests` for Mapbox geocoding
- CORS enabled

### Database
- PostgreSQL
- Existing entities in code/schema include:
  - `places`
  - `hechshers`
  - `hechsher_aliases`
  - `place_tags`
  - `place_hechshers`
  - `users`
  - `user_preferred_hechshers`
  - `submissions`
  - `refresh_token_families`
  - `refresh_tokens`
  - `revoked_tokens`

## 4) Roles
- Anonymous user
- Authenticated user
- Admin

## 5) Functional Requirements

### 5.1 Map and Marker Display
1. On app load, map renders and requests user location.
2. If location permission granted, map centers on user location.
3. If denied/unavailable, map defaults to center on Jerusalem (31.7683°N, 35.2137°E).
4. Place markers are shown for places matching active filters.
5. Marker icons display the hechsher symbol (icon) for each place's primary hechsher.
6. Clicking on a map location (but not on a marker) centers and zooms the map to that location.
7. When user selects a suggestion from the search dropdown, the map centers on and zooms to that location.

### 5.2 Search and Filter
1. Hechsher filter supports multiple selections (multi-select dropdown).
2. Hechsher filter supports typeahead search across:
   - hechsher display name
   - any hechsher alias
3. Hechsher suggestions show display name and icon.
4. Place search supports name, tags, and proximity radius.
5. Frontend search UX is a unified place+location typeahead dropdown.
6. Proximity search supports both:
   - current location + radius
   - typed location + radius
7. Places can have multiple hechshers.
8. Radius units are user-switchable between miles and kilometers.
9. Default radius is 1 mile.
10. Maximum radius is 10 miles (16.09 km when unit is km).
11. Backend clamps oversized radius values to the configured maximum.
12. `GET /api/places` accepts both `tags[]` and `tags` query key variants.
13. Typed location suggestions are available from `GET /api/locations/search`.
14. Search radius is calculated from the center of the visible map (not from current user location, unless user just loaded the page).
15. A "Reset Filters" button clears all active filters, including selected hechshers, search query, tags, and radius.

### 5.3 Preferences
1. Authenticated users can save preferred hechshers via the preferences page.
2. Preferences page is accessible from user menu/navigation.
3. Preferences page shows all available hechshers with icons and display names, with toggles or multi-select to add/remove preferences.
4. Preferences stored via many-to-many `user_preferred_hechshers`.
5. No preference ranking/ordering required.
6. Default map filtering uses preferences when present.
7. Preference changes are saved immediately without requiring form submission.

### 5.4 Submissions and Tagging
1. Users can submit new place manually.
2. Manual submission requires: name, address, at least one hechsher, tags.
3. Users can submit using location detection for coordinates/address assist.
4. Anonymous users can tag existing places.
5. Users can add place aliases to an existing place (login required); alias additions pass through moderation pipeline.
6. Submission rate limit: one successful submission per minute.
7. Only approved submissions count toward rate limit; failed submissions do not increment the rate limit counter.
8. Current implementation captures coordinates but does not yet enforce a strict 100-foot verification threshold.
9. Anonymous submission limiter key uses device cookie, with IP fallback if cookie is missing.
10. Entry creation uses a dedicated submission form.
11. Submission form includes:
    - Place name field
    - Address field with typeahead dropdown suggestions (enforces selecting/entering a valid address)
    - Hechsher field as searchable dropdown with multi-select, ability to search existing hechshers, and an "Add New Hechsher" button that opens a modal form to create a new hechsher (with fields for display name, aliases, and icon upload)
    - Tags field
    - Save and Close buttons; form can be closed via an X button in the top-right corner
12. Entry editing is allowed for logged-in users only; edit opens the creation form prefilled with current values.
13. Place detail views include a `tag` action for all users and an `edit` action for logged-in users.
14. Edits follow the same moderation path as creations.
15. Tag updates are moderated; if proposed tags are inconsistent with existing tags, they are auto-flagged.
16. Alias updates are moderated; if proposed aliases are inconsistent with existing aliases, they are auto-flagged.
17. Anonymous submission limiter key priority is authenticated user ID -> `device_id` cookie -> remote IP.
18. Backend automatically issues a `device_id` cookie for anonymous anti-abuse tracking.

### 5.5 Moderation
1. AI classifies each submission as `approved` or `flagged`.
2. All submissions are shown in admin queue UI, split into two sections:
   - flagged
   - non-flagged
3. Admin review page is accessible only to users with `user_status = admin`.
4. Admin review page displays submission queue with human-readable summaries:
   - For `new_place` submissions: place name, address, hechshers, tags.
   - For `tag_update` submissions: place name, proposed tags, change reason.
   - For `edit` submissions: clear before/after comparison of changed fields.
5. Non-flagged submissions publish immediately to map.
6. Admin can approve/reject queued items.
7. Logged-in user can see status of only their own submissions.
8. On submission by logged-in user, submission/place reference is linked to their account.
9. Moderation fields are standardized as:
   - `spam_filter_result`: `approved` | `flagged`
   - `admin_review_status`: `pending_review` | `approved` | `rejected`
   - `admin_reject_reason`: nullable text (set on reject)
10. Visibility rule:
    - visible when `spam_filter_result = approved` OR `admin_review_status = approved`
    - hidden otherwise by default
    - `admin_review_status = rejected` always overrides and removes/hides from live map data
11. Rejected entries are removed from live map data, but submission history is retained for user status and audit.
12. Admin review UI shows full proposed entry/edit payload and supports `approve` and `reject` actions.
13. MVP moderation integration uses a single Anthropic API classification call plus deterministic server-side rules; framework orchestration is out of scope.
14. If `ANTHROPIC_API_KEY` is not configured, moderation auto-approves in dev/test environments.
15. If moderation service call fails unexpectedly, submission defaults to `flagged`.
16. Rejecting a previously published `new_place` currently deactivates the place (`is_active=false`) instead of hard-deleting it.

### 5.6 Auth and Session Security
1. Auth uses access + refresh JWT tokens.
2. Access token TTL: 15 minutes.
3. Refresh token TTL: 30 days.
4. Refresh token rotates on every refresh call.
5. Tokens are stored in `httpOnly` cookies.
6. CSRF protection uses the double-submit cookie pattern on state-changing requests.
7. CSRF cookie bootstrap/refresh endpoint is `GET /api/csrf-token`.
8. CSRF cookie is intentionally readable by browser JS so it can be echoed in `X-CSRF-Token`.
9. Cookie policy:
   - production: `Secure=true`, `HttpOnly=true`, `SameSite=Lax`
   - local development: `Secure=false`, `HttpOnly=true`, `SameSite=Lax`
10. Revocation/blocklist is required for logout, password change, and account deletion.
11. Logout revokes current session/token family only.
12. Password change and account deletion revoke all active sessions for the user.
13. Refresh-token reuse detection revokes the entire token family and forces re-authentication.

## 6) User Stories + Acceptance Criteria

### US-01 View map markers
As a user, I want to open the app and see nearby places on a map.

Acceptance criteria:
- Map loads successfully.
- Markers are visible for currently matched places.
- If geolocation succeeds, map centers near user location.
- If geolocation fails, map centers to configured fallback.

### US-02 Filter by hechsher with alias support
As a user, I want to filter by hechsher using searchable suggestions with icons and multiple selections.

Acceptance criteria:
- Typing hechsher name returns matching hechshers.
- Typing any alias returns canonical hechsher result.
- Suggestions include hechsher icon and display name.
- User can select multiple hechshers to filter by.
- Selecting hechshers updates map markers to show places with any of the selected hechshers.

### US-03 Search by name/tag/proximity
As a user, I want to search places by name, tags, and distance.

Acceptance criteria:
- Search by place name returns matching places.
- Search by tag (e.g., `meat`, `dairy`, `bakery`) filters results.
- Radius search works with current location.
- Radius search works with typed location.
- Radius units are switchable between mi/km.
- Default radius is 1 mile.
- Maximum radius is 10 miles (16.09 km).
- Radius is calculated from the center of the visible map.
- Reset Filters button clears all active filters including hechshers, search query, tags, and radius.

### US-04 Create account and save preferences
As a user, I want to create an account and save preferred hechshers.

Acceptance criteria:
- User can register and log in using JWT-based auth.
- User can add/remove preferred hechshers.
- On next login/app load, map defaults to preferred hechsher filtering when preferences exist.

### US-05 Add places manually
As a contributor, I want to add a place manually.

Acceptance criteria:
- Submission form validates required fields: name, address, hechsher, tags.
- Address field offers typeahead suggestions of real addresses via geocoding; user must select or enter a valid address.
- Hechsher field supports searching existing hechshers with an "Add New Hechsher" button.
- Adding a new hechsher opens a modal form with fields: display name, aliases, and icon upload.
- Submission creates place + place-hechsher + tags relations.
- Place with multiple hechshers is supported.
- For logged-in edit flow, the same form is prefilled with existing entry data.
- Form can be closed via X button in the top-right corner.

### US-06 Add places with location detection
As a contributor, I want my current location to help populate place coordinates/address.

Acceptance criteria:
- App can capture device coordinates (with permission).
- Coordinates are attached to submission.
- Address can be prefilled via geocoding or entered manually if unresolved.
- Verification distance threshold is 100 feet.
- When user selects a location from the search dropdown, the map centers on and zooms to that location.

### US-07 Tag and alias existing places
As a user, I want to tag and add aliases to an existing place.

Acceptance criteria:
- Anonymous users can add tags to an existing place.
- Logged-in users can add aliases (alternative names) to an existing place.
- Tag and alias updates are persisted and reflected in search/filter.
- Tag and alias submissions pass through moderation.
- Inconsistent tag proposals are auto-flagged for admin review.
- Inconsistent alias proposals are auto-flagged for admin review.

### US-08 Moderation visibility and admin actions
As an admin, I want to review all submissions and act on flagged content.

Acceptance criteria:
- Admin page exists in frontend.
- Admin queue has separate flagged and non-flagged sections.
- Admin can approve or reject queued entries.
- Admin can view full proposed entry/edit payload before deciding.
- Non-flagged entries are visible on map immediately after submission.
- `admin_review_status = rejected` always removes/hides content from live map data.
- Rejected entries remain in submission history with status `rejected`.

### US-09 User upload status tracking
As a logged-in user, I want to view statuses for my submissions.

Acceptance criteria:
- User can view list of own submissions only on the "My Submissions" page.
- Each submission displays in human-readable format (not raw JSON):
  - For `new_place`: place name, address, hechshers, tags, moderation status.
  - For `tag_update`: place name, proposed tags, moderation status.
  - For `edit`: place name, summary of changes, moderation status.
- Each submission shows moderation status (`approved`, `flagged`, `rejected`, pending, etc. per final state model).
- User cannot view other users' submission statuses.

### US-10 Manage preferred hechshers
As a logged-in user, I want to manage my list of preferred hechshers via a dedicated preferences page.

Acceptance criteria:
- Preferences page is accessible from user menu/navigation.
- Preferences page displays all available hechshers with icons and display names.
- User can toggle hechshers on/off to add/remove from preferences using checkboxes or toggles.
- Preferences are saved immediately without requiring form submission.
- Selecting hechshers as preferences updates the default map filter on next load.

### US-11 Admin review and moderate submissions
As an admin, I want to review and moderate user submissions with a dedicated admin interface.

Acceptance criteria:
- Admin page is accessible only to users with `user_status = admin`.
- Admin page displays submission queue split into flagged and non-flagged sections.
- Each submission shows human-readable summary (not raw JSON):
  - For `new_place`: place name, address, hechshers, tags, AI moderation decision.
  - For `tag_update`: place name, proposed tags, change reason, AI moderation decision.
  - For `edit`: place name, before/after comparison of changes, AI moderation decision.
  - For `alias_update`: place name, proposed aliases, change reason, AI moderation decision.
- Admin can approve or reject each submission with optional reason for rejection.
- Approved submissions are published to the map.
- Rejected submissions are removed from the map and stored in history.

## 7) Data Model (Target MVP)

Note: this section defines target entities/relations for MVP. Existing schema/code may require migration.

### 7.1 `places`
- `place_id` (PK)
- `place_name`
- `street_address`
- `latitude` (numeric)
- `longitude` (numeric)
- `date_added`
- `is_active` (soft visibility/deactivation flag)

### 7.2 `hechshers`
- `hechsher_id` (PK)
- `hechsher_display_name` (unique)
- `hechsher_symbol` (icon URL/path)

### 7.3 `hechsher_aliases`
- `hechsher_id` (FK)
- `hechsher_alias`
- composite PK (`hechsher_id`, `hechsher_alias`)

### 7.4 `place_hechshers`
- `place_id` (FK)
- `hechsher_id` (FK)
- `place_hechsher_marking_verity` (existing enum field retained)
- composite PK (`place_id`, `hechsher_id`)

### 7.5 `place_aliases` (new)
- `place_id` (FK)
- `place_alias` (string, alternative name for the place)
- composite PK (`place_id`, `place_alias`)

### 7.6 `place_tags`
- `place_id` (FK)
- `place_tag` (enum)
- composite PK (`place_id`, `place_tag`)

### 7.7 `users`
- `user_id` (PK)
- `user_email` (unique)
- `user_name` (unique or constrained)
- `user_password` (hashed)
- `user_status` (`admin`, `basic`)
- `user_since_date`

### 7.8 `user_preferred_hechshers` (new)
- `user_id` (FK)
- `hechsher_id` (FK)
- composite PK (`user_id`, `hechsher_id`)

### 7.9 `submissions` (new)
Tracks ingestion + moderation independently of canonical place records.

Suggested fields:
- `submission_id` (PK)
- `submitted_by_user_id` (nullable FK; null for anonymous)
- `place_id` (nullable FK if creating/updating existing place)
- `submission_type` (`new_place`, `tag_update`, `edit`, `alias_update`)
- `payload_json`
- `spam_filter_result` (`approved`, `flagged`)
- `admin_review_status` (`pending_review`, `approved`, `rejected`)
- `admin_reject_reason` (nullable text)
- `is_visible` (derived or materialized according to visibility rule)
- `published_at` (nullable)
- `created_at`
- `updated_at`

Retention behavior:
- This table is the permanent moderation/status history for logged-in user tracking.
- Rejected submissions are not hard-deleted from this table.
- If a rejected submission created/changed canonical map entities, those live entities are reverted/hidden; history remains.
- If submitting user deletes their account, set `submitted_by_user_id` to `NULL`; submission and content history remain.

### 7.10 `refresh_token_families`
- `family_id` (PK)
- `user_id` (FK)
- `revoked` (boolean)
- `created_at`
- `revoked_at` (nullable)

### 7.11 `refresh_tokens`
- `jti` (PK)
- `family_id` (FK)
- `user_id` (FK)
- `used` (boolean)
- `created_at`
- `used_at` (nullable)

### 7.12 `revoked_tokens`
- `jti` (PK)
- `token_type` (`access` | `refresh`)
- `user_id` (FK)
- `revoked_at`
- `expires_at`

## 8) API Surface (MVP Contract)

### Public
- `GET /api/csrf-token`
  - issues/refreshes CSRF cookie and returns `csrf_token`
- `GET /api/places`
  - supports filters: `hechsher`, `hechsher_id`, `q`, `tags[]|tags`, `radius`, `unit=mi|km`, `lat/lng` or `location_query`
  - when authenticated and no hechsher filter is passed, defaults to preferred hechshers
- `GET /api/hechshers/search?q=`
  - returns canonical hechshers by name/alias with icon
- `GET /api/locations/search?q=`
  - returns location suggestions (`place_name`, `lat`, `lng`)
  - used for both location typeahead in map search and address field typeahead in submission form
- `POST /api/hechshers`
  - creates a new hechsher
  - Auth: optional (anonymous allowed for MVP)
  - CSRF required
  - Request body: name, aliases (array), icon file upload
  - Moderated submission (similar to place submissions)
- `GET /api/places/{id}/aliases`
  - returns existing aliases for a place
- `POST /api/submissions/place`
  - anonymous or authenticated
  - rate limited to 1 successful submission/minute per user or anonymous client key
  - only successful submissions increment the rate limit counter; failed submissions do not
  - anonymous limiter key: device cookie, IP fallback
  - supports `submission_type`: `new_place`, `edit`, `tag_update`, `alias_update`
- `POST /api/places/{id}/tags`
  - anonymous allowed
  - routed through moderation pipeline
- `POST /api/places/{id}/aliases`
  - authenticated required
  - routed through moderation pipeline
  - request body: array of new aliases
- typed location resolution for proximity search is backed by Mapbox geocoding

### Authenticated
- `POST /auth/register`
- `POST /auth/login` (JWT)
- `POST /auth/refresh`
- `POST /auth/logout` (revokes current token family)
- `GET /api/me/preferences/hechshers`
- `PUT /api/me/preferences/hechshers`
- `GET /api/me/submissions`
- `POST /auth/change-password` (revokes all active sessions)
- `DELETE /auth/account` (anonymizes ownership refs and revokes all active sessions)
- No dedicated `GET /api/me` profile endpoint is defined in MVP; user payload is returned on login/register.

### Admin
- `GET /api/admin/submissions?spam_filter_result=flagged|approved`
  - also supports `admin_review_status`, `page`, `page_size`
- `GET /api/admin/submissions/{id}` (full submission payload for review)
- `POST /api/admin/submissions/{id}/approve`
- `POST /api/admin/submissions/{id}/reject`

### OpenAPI Contract Requirement
- The backend API must be documented in OpenAPI 3.1 style.
- Each endpoint must define:
  - request body schema
  - response schemas per status code
  - auth/security requirements
  - error response schema (`code`, `message`, optional `details`)
- The OpenAPI document is part of MVP deliverables and is used as the frontend/backend contract.

### OpenAPI 3.1 Schema Baseline (MVP)
The following contract is normative for MVP implementation.

#### Security Schemes
- `cookieAuthAccess`: access JWT in `access_token` cookie.
- `cookieAuthRefresh`: refresh JWT in `refresh_token` cookie.
- `csrfHeader`: `X-CSRF-Token` required for state-changing requests.

#### Shared Error Schema
```json
{
  "code": "string",
  "message": "string",
  "details": {}
}
```

#### Core Data Schemas

`Place`
```json
{
  "place_id": 123,
  "place_name": "Falafel HaKosem",
  "street_address": "Shlomo HaMelech 1, Tel Aviv",
  "latitude": 32.0700,
  "longitude": 34.7760,
  "hechshers": [
    {
      "hechsher_id": 7,
      "hechsher_display_name": "בד\"ץ העדה החרדית",
      "hechsher_symbol": "https://.../badatz.png"
    }
  ],
  "tags": ["restaurant", "meat"],
  "distance": {
    "value": 0.7,
    "unit": "mi"
  }
}
```

`HechsherSearchResult`
```json
{
  "hechsher_id": 7,
  "hechsher_display_name": "Badatz",
  "hechsher_symbol": "https://.../badatz.png",
  "matched_alias": "בד\"ץ"
}
```

`Submission`
```json
{
  "submission_id": 981,
  "submitted_by_user_id": 42,
  "place_id": 123,
  "submission_type": "edit",
  "payload_json": {},
  "spam_filter_result": "flagged",
  "admin_review_status": "pending_review",
  "admin_reject_reason": null,
  "is_visible": false,
  "published_at": null,
  "created_at": "2026-06-15T18:23:00Z",
  "updated_at": "2026-06-15T18:23:00Z"
}
```

`AuthUser`
```json
{
  "user_id": 42,
  "user_email": "yael@example.com",
  "user_name": "Yael",
  "user_status": "basic",
  "preferred_hechshers": [7, 9]
}
```

#### Endpoint Schemas

`GET /api/csrf-token`
- `200` response:
```json
{
  "csrf_token": "string"
}
```

`GET /api/places`
- Query params:
  - `q` string (place name / free text)
  - `hechsher` string or `hechsher_id` int
  - `tags[]` enum array (backend also accepts `tags`)
  - `radius` number
  - `unit` enum: `mi|km`
  - `lat`, `lng` numbers OR `location_query` string
- `200` response:
```json
{
  "items": ["Place"],
  "count": 1
}
```
- `400` invalid query -> `Error`

`GET /api/locations/search?q=`
- Query params:
  - `q` required string
  - `limit` optional int default 8
- `200` response:
```json
{
  "items": [
    {
      "place_name": "Jerusalem, Israel",
      "lat": 31.7683,
      "lng": 35.2137
    }
  ]
}
```
- `503` dependent geocoding service unavailable

`GET /api/hechshers/search?q=`
- Query params:
  - `q` required string
  - `limit` optional int default 10 max 50
- `200` response:
```json
{
  "items": ["HechsherSearchResult"],
  "count": 2
}
```

`POST /api/submissions/place`
- Auth: optional (anonymous allowed)
- CSRF required.
- Rate limit: 1 successful submission/minute per user or anonymous client key (failed submissions do not count).
- Supports `submission_type`: `new_place`, `edit`, `tag_update`, `alias_update`.
- For `edit`/`tag_update`/`alias_update`, `place_id` is required.
- Edit and alias_update currently require authenticated user.
- Request body:
```json
{
  "submission_type": "new_place",
  "place_id": null,
  "place_name": "Falafel HaKosem",
  "street_address": "Shlomo HaMelech 1, Tel Aviv",
  "latitude": 32.0700,
  "longitude": 34.7760,
  "hechsher_ids": [7],
  "tags": ["restaurant", "meat"],
  "source": "manual"
}
```
- `201` response:
```json
{
  "submission": "Submission",
  "published": true,
  "message": "Submitted successfully"
}
```
- `429` rate limit -> `Error`

`POST /api/places/{id}/tags`
- Auth: optional (anonymous allowed)
- CSRF required.
- Request body:
```json
{
  "tags": ["dairy", "cafe"],
  "reason": "menu changed"
}
```
- `201` response:
```json
{
  "submission": "Submission",
  "published": false
}
```

`POST /api/hechshers`
- Auth: optional (anonymous allowed for MVP; may require moderation)
- CSRF required.
- Request body (multipart form-data):
  - `name` string (hechsher display name)
  - `aliases` array of strings (alternative names)
  - `icon` file upload (image file for hechsher symbol)
- `201` response:
```json
{
  "hechsher": {
    "hechsher_id": 123,
    "hechsher_display_name": "New Hechsher",
    "hechsher_symbol": "https://.../hechsher_123.png"
  },
  "submission_id": 456,
  "message": "Hechsher submitted for review"
}
```

`POST /api/places/{id}/aliases`
- Auth: authenticated required
- CSRF required.
- Request body:
```json
{
  "aliases": ["Alternative Name 1", "Alternative Name 2"],
  "reason": "adding known aliases"
}
```
- `201` response:
```json
{
  "submission": "Submission",
  "published": false
}
```

`POST /auth/register`
- CSRF required.
- Request body:
```json
{
  "email": "user@example.com",
  "username": "user123",
  "password": "StrongPassword123!"
}
```
- `201` response:
```json
{
  "user": "AuthUser"
}
```

`POST /auth/login`
- CSRF required.
- Request body:
```json
{
  "email": "user@example.com",
  "password": "StrongPassword123!"
}
```
- `200` response:
```json
{
  "user": "AuthUser",
  "message": "Logged in"
}
```
- Sets `access_token`, `refresh_token`, and CSRF cookie.

`POST /auth/refresh`
- Auth: refresh cookie required.
- CSRF required.
- `200` response:
```json
{
  "message": "Token refreshed"
}
```
- Rotates refresh token; reuse detection revokes family.

`POST /auth/logout`
- Auth: access cookie required.
- CSRF required.
- `200` response:
```json
{
  "message": "Logged out"
}
```
- Revokes current session/token family and clears auth cookies.

`POST /auth/change-password`
- Auth: access cookie required.
- CSRF required.
- Request body:
```json
{
  "current_password": "OldPass123!",
  "new_password": "NewPass123!"
}
```
- `200` response:
```json
{
  "message": "Password changed"
}
```
- Revokes all active sessions for user.

`DELETE /auth/account`
- Auth: access cookie required.
- CSRF required.
- `200` response:
```json
{
  "message": "Account deleted"
}
```
- Sets submission ownership refs to null and revokes all active sessions.

`GET /api/me/preferences/hechshers`
- Auth: access cookie required.
- `200` response:
```json
{
  "hechsher_ids": [7, 9]
}
```

`PUT /api/me/preferences/hechshers`
- Auth: access cookie required.
- CSRF required.
- Request body:
```json
{
  "hechsher_ids": [7, 9]
}
```
- `200` response:
```json
{
  "hechsher_ids": [7, 9],
  "message": "Preferences saved"
}
```

`GET /api/me/submissions`
- Auth: access cookie required.
- Query params: `status` optional, `page` optional, `page_size` optional.
- `200` response:
```json
{
  "items": ["Submission"],
  "count": 1,
  "page": 1,
  "page_size": 20
}
```

`GET /api/admin/submissions?spam_filter_result=flagged|approved`
- Auth: admin access required.
- Query params: `spam_filter_result` optional, `admin_review_status` optional, `page` optional, `page_size` optional.
- `200` response:
```json
{
  "items": ["Submission"],
  "count": 15
}
```

`GET /api/admin/submissions/{id}`
- Auth: admin access required.
- `200` response:
```json
{
  "submission": "Submission"
}
```

`POST /api/admin/submissions/{id}/approve`
- Auth: admin access required.
- CSRF required.
- `200` response:
```json
{
  "submission_id": 981,
  "admin_review_status": "approved",
  "is_visible": true
}
```

`POST /api/admin/submissions/{id}/reject`
- Auth: admin access required.
- CSRF required.
- Request body:
```json
{
  "reason": "Insufficient evidence"
}
```
- `200` response:
```json
{
  "submission_id": 981,
  "admin_review_status": "rejected",
  "is_visible": false
}
```

#### Global Response Rules
- `400`: invalid query
- `401`: unauthenticated
- `403`: authenticated but insufficient permissions
- `404`: missing resource
- `409`: conflict (duplicate, stale moderation transition, etc.)
- `422`: validation failure
- `429`: rate limited
- `503`: dependent service unavailable (e.g., geocoding)
