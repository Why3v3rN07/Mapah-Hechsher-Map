# Mapah Product + Technical Spec (Spec-Driven Development)

## 1) Purpose
Mapah helps users find nearby places to eat based on kosher certifications (hechshers) they follow.

This spec is the source of truth for implementation planning and acceptance.

## 2) Scope and Phases

### MVP (In Scope)
- View a Mapbox map with place markers.
- Search/filter places by:
  - hechsher (searchable dropdown with icon + alias matching)
  - place name
  - place tags
  - proximity radius from current location or typed location
- Account system with JWT auth.
- Logged-in users can save preferred hechshers.
- Map defaults:
  - logged-in + preferences exist: show places matching preferred hechshers
  - otherwise: show all places
- Add place manually (required fields: name, address, hechsher, tags).
- Add place with location detection for address/coordinates.
- Tag existing places (anonymous allowed).
- AI spam moderation is implemented via a direct Anthropic API call with structured JSON output (no LangChain/agent orchestration in MVP).
- Admin queue UI in frontend with separate sections for flagged vs non-flagged.
- Non-flagged submissions appear immediately on map.
- Logged-in users can view upload status for their own submissions.
- Typed location search/geocoding uses Mapbox geocoding APIs.
- Submission anti-abuse: max one submission per minute per user (or per anonymous client key).

### Future (Out of MVP)
- Certificate OCR.
- Expanded verification levels/business logic (field exists; keep schema support).

## 3) Current Stack Baseline (from codebase)

### Frontend
- React + Vite (`mapah-frontend`)
- `mapbox-gl`
- ESLint

### Backend
- Flask app factory (`mapah-backend/app/__init__.py`)
- Flask-SQLAlchemy + Flask-Migrate
- JWT library installed (`Flask-JWT-Extended`)
- Flask-Login also present in current code (migration/cleanup decision pending)
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

## 4) Roles
- Anonymous user
- Authenticated user
- Admin

## 5) Functional Requirements

### 5.1 Map and Marker Display
1. On app load, map renders and requests user location.
2. If location permission granted, map centers on user location.
3. If denied/unavailable, map uses default fallback center.
4. Place markers are shown for places matching active filters.

### 5.2 Search and Filter
1. Hechsher filter supports typeahead search across:
   - hechsher display name
   - any hechsher alias
2. Hechsher suggestions show display name and icon.
3. Place search supports name, tags, and proximity radius.
4. Proximity search supports both:
   - current location + radius
   - typed location + radius
5. Places can have multiple hechshers.
6. Radius units are user-switchable between miles and kilometers.
7. Default radius is 1 mile.
8. Maximum radius is 10 miles (16.09 km when unit is km).

### 5.3 Preferences
1. Authenticated users can save preferred hechshers.
2. Preferences stored via many-to-many `user_preferred_hechshers`.
3. No preference ranking/ordering required.
4. Default map filtering uses preferences when present.

### 5.4 Submissions and Tagging
1. Users can submit new place manually.
2. Manual submission requires: name, address, at least one hechsher, tags.
3. Users can submit using location detection for coordinates/address assist.
4. Anonymous users can tag existing places.
5. Submission rate limit: one submission per minute.
6. Address/location verification threshold is within 100 feet.
7. Anonymous submission limiter key uses device cookie, with IP fallback if cookie is missing.
8. Entry creation uses a dedicated submission form.
9. Entry editing is allowed for logged-in users only; edit opens the creation form prefilled with current values.
10. Place detail views include a `tag` action for all users and an `edit` action for logged-in users.
11. Edits follow the same moderation path as creations.
12. Tag updates are moderated; if proposed tags are inconsistent with existing tags, they are auto-flagged.

### 5.5 Moderation
1. AI classifies each submission as `approved` or `flagged`.
2. All submissions are shown in admin queue UI, split into two sections:
   - flagged
   - non-flagged
3. Non-flagged submissions publish immediately to map.
4. Admin can approve/reject queued items.
5. Logged-in user can see status of only their own submissions.
6. On submission by logged-in user, submission/place reference is linked to their account.
7. Moderation fields are standardized as:
   - `spam_filter_result`: `approved` | `flagged`
   - `admin_review_status`: `pending_review` | `approved` | `rejected`
8. Visibility rule:
   - visible when `spam_filter_result = approved` OR `admin_review_status = approved`
   - hidden otherwise by default
   - `admin_review_status = rejected` always overrides and removes/hides from live map data
9. Rejected entries are removed from live map data, but submission history is retained for user status and audit.
10. Admin review UI shows full proposed entry/edit payload and supports `approve` and `reject` actions.
11. MVP moderation integration uses a single Anthropic API classification call plus deterministic server-side rules; framework orchestration is out of scope.

### 5.6 Auth and Session Security
1. Auth uses access + refresh JWT tokens.
2. Access token TTL: 15 minutes.
3. Refresh token TTL: 30 days.
4. Refresh token rotates on every refresh call.
5. Tokens are stored in `httpOnly` cookies.
6. CSRF protection uses the double-submit cookie pattern on state-changing requests.
7. Cookie policy:
   - production: `Secure=true`, `HttpOnly=true`, `SameSite=Lax`
   - local development: `Secure=false`, `HttpOnly=true`, `SameSite=Lax`
8. Revocation/blocklist is required for logout, password change, and account deletion.
9. Logout revokes current session/token family only.
10. Password change and account deletion revoke all active sessions for the user.
11. Refresh-token reuse detection revokes the entire token family and forces re-authentication.

## 6) User Stories + Acceptance Criteria

### US-01 View map markers
As a user, I want to open the app and see nearby places on a map.

Acceptance criteria:
- Map loads successfully.
- Markers are visible for currently matched places.
- If geolocation succeeds, map centers near user location.
- If geolocation fails, map centers to configured fallback.

### US-02 Filter by hechsher with alias support
As a user, I want to filter by hechsher using searchable suggestions with icons.

Acceptance criteria:
- Typing hechsher name returns matching hechshers.
- Typing any alias returns canonical hechsher result.
- Suggestions include hechsher icon and display name.
- Selecting a hechsher updates map markers.

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
- Submission creates place + place-hechsher + tags relations.
- Place with multiple hechshers is supported.
- For logged-in edit flow, the same form is prefilled with existing entry data.

### US-06 Add places with location detection
As a contributor, I want my current location to help populate place coordinates/address.

Acceptance criteria:
- App can capture device coordinates (with permission).
- Coordinates are attached to submission.
- Address can be prefilled via geocoding or entered manually if unresolved.
- Verification distance threshold is 100 feet.

### US-07 Tag existing places anonymously
As an anonymous user, I want to tag an existing place.

Acceptance criteria:
- Anonymous request can add tags to an existing place.
- Tag update is persisted and reflected in search/filter.
- Tag submissions pass through moderation.
- Inconsistent tag proposals are auto-flagged for admin review.

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
- User can view list of own submissions only.
- Each submission shows moderation status (`approved`, `flagged`, `rejected`, etc. per final state model).
- User cannot view other users' submission statuses.

## 7) Data Model (Target MVP)

Note: this section defines target entities/relations for MVP. Existing schema/code may require migration.

### 7.1 `places`
- `place_id` (PK)
- `place_name`
- `street_address`
- `latitude` (numeric)
- `longitude` (numeric)
- `date_added`
- optional operational status fields as needed

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

### 7.5 `place_tags`
- `place_id` (FK)
- `place_tag` (enum)
- composite PK (`place_id`, `place_tag`)

### 7.6 `users`
- `user_id` (PK)
- `user_email` (unique)
- `user_name` (unique or constrained)
- `user_password` (hashed)
- `user_status` (`admin`, `basic`)
- `user_since_date`

### 7.7 `user_preferred_hechshers` (new)
- `user_id` (FK)
- `hechsher_id` (FK)
- composite PK (`user_id`, `hechsher_id`)

### 7.8 `submissions` (new)
Tracks ingestion + moderation independently of canonical place records.

Suggested fields:
- `submission_id` (PK)
- `submitted_by_user_id` (nullable FK; null for anonymous)
- `place_id` (nullable FK if creating/updating existing place)
- `submission_type` (`new_place`, `tag_update`, `edit`)
- `payload_json`
- `spam_filter_result` (`approved`, `flagged`)
- `admin_review_status` (`pending_review`, `approved`, `rejected`)
- `is_visible` (derived or materialized according to visibility rule)
- `published_at` (nullable)
- `created_at`
- `updated_at`

Retention behavior:
- This table is the permanent moderation/status history for logged-in user tracking.
- Rejected submissions are not hard-deleted from this table.
- If a rejected submission created/changed canonical map entities, those live entities are deleted or reverted; history remains.
- If submitting user deletes their account, set `submitted_by_user_id` to `NULL`; submission and content history remain.

## 8) API Surface (MVP Contract)

### Public
- `GET /api/places`
  - supports filters: `hechsher`, `q`, `tags[]`, `radius`, `unit=mi|km`, `lat/lng` or `location_query`
- `GET /api/hechshers/search?q=`
  - returns canonical hechshers by name/alias with icon
- `POST /api/submissions/place`
  - anonymous or authenticated
  - rate limited to 1 submission/minute
  - anonymous limiter key: device cookie, IP fallback
- `POST /api/places/{id}/tags`
  - anonymous allowed
  - routed through moderation pipeline
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

### Admin
- `GET /api/admin/submissions?spam_filter_result=flagged|approved`
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
  "is_visible": false,
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

`GET /api/places`
- Query params:
  - `q` string (place name / free text)
  - `hechsher` string or `hechsher_id` int
  - `tags[]` enum array
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
- Rate limit: 1/minute per user or anonymous client key.
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

`POST /auth/register`
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
- `401`: unauthenticated
- `403`: authenticated but insufficient permissions
- `404`: missing resource
- `409`: conflict (duplicate, stale moderation transition, etc.)
- `422`: validation failure
- `429`: rate limited
