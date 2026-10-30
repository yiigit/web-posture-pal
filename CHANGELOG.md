# Changelog

## Unreleased

- Use MySQL 8.4 for Docker persistence through a portable SQLAlchemy/PyMySQL layer.
- Add an opt-in, idempotent demo fixture with profiles, social activity and friendships.
- Add a transactional read-only SQLite-to-MySQL importer that refuses nonempty destinations.
- Add live MySQL integration checks and database-aware health checks.

## 0.10.0 — 2026-10-30

- Add friend requests, acceptance, removal and blocking with account-based authentication.
- Add explicit private/friends-only activity sharing, access-controlled share links, cheers and comments.
- Add privacy controls enforced by the backend on feed, direct activity reads and engagement.
- Add social statistics in the community page and home dashboard.
- Persist social records with account deletion cascades and throttle posting, commenting and requests.

## 0.9.2 — 2026-10-30

- Use persistent shared left navigation on every page, including account and admin screens.
- Keep an accessible compact left rail visible on phones and highlight the current section.
- Preserve the library saved-movements toggle in the shared navigation.

## 0.9.1 — 2026-10-30

- Show the signed-in profile, initials and role at the top of app and administration pages.
- Add a sign-in shortcut for guests and refresh profile details after account changes.

## 0.9.0 — 2026-10-30

- Add registration, sign-in/out, editable profiles, password changes and self-service account deletion.
- Add admin user search/pagination, account creation, roles, enable/disable, profile editing, password resets and deletion.
- Add scrypt password hashing, expiring/revocable hashed sessions, CSRF request verification and authentication throttling.
- Preserve bootstrap admin tokens and protect the last active admin account.
- Add persistent user/session tables without replacing catalog data.

## 0.8.0 — 2026-10-30

- Add dashboard habit completion and body-area coverage charts.
- Add quick-movement counts, average catalog duration and saved-library percentage.
- Keep daily activity and catalog statistics clearly labeled, with loading, error and empty states.

## 0.7.1 — 2026-10-30

- Add shared left navigation to the breaks page with an active-page indicator.
- Reuse the sidebar on the dashboard and adjust break layouts for narrower screens.

## 0.7.0 — 2026-10-30

- Make the wellbeing dashboard the default start page.
- Add daily progress cards, interactive habit checklist, movement inspiration and coaching shortcuts.
- Move the movement library to `/library.html` and update navigation.
- Refresh browser-saved daily progress when returning to the page.

## 0.6.0 — 2026-10-30

- Add Enhanced Break System with standard, comfort/pain relief, strength and movement-habit routines.
- Add elapsed-time break timers and optional in-page reminders with snooze/skip controls.
- Add desk and phone contextual posture self-checks.
- Add browser-persisted daily habit progress and break counts with local calendar rollover.
- Add a dedicated break coaching bounded context and typed API endpoints.

## 0.5.0 — 2026-10-30

- Add an authenticated admin dashboard with live library metrics and body-area/position coverage.
- Add protected dashboard API and navigation between overview and exercise management.
- Refresh dashboard metrics after catalog changes and on demand.

## 0.4.0 — 2026-10-30

- Add durable SQLite exercise storage, seeded once from the initial catalog.
- Add validated create, update and delete API endpoints protected with an administrator bearer token.
- Add authenticated exercise management UI with create/edit forms and delete confirmation.
- Add fail-closed admin configuration, security response headers, persistent Docker storage, and secret configuration guidance.
- Add authorization, validation, persistence and CRUD integration tests.

## 0.3.2 — 2026-10-30

- Remove the Nike wordmark and swoosh asset, retaining the orange-and-black theme.

## 0.3.1 — 2026-10-30

- Restyle the Nike theme with an orange campaign hero, warm exercise cards, and black typography.
- Add Nike wordmark and swoosh treatment with responsive branding.
- Rename the appearance option to Nike Orange.

## 0.3.0 — 2026-10-30

- Add Light, Dark, Sportive, and Nike-inspired appearance options.
- Introduce shared palette tokens for the library, illustrations, controls and exercise dialog.
- Persist theme selection in the browser and restore it before styles load.
- Add responsive, keyboard-accessible appearance selector.

## 0.2.0 — 2026-10-30

- Replace the standard-library HTTP server with FastAPI and Uvicorn.
- Add typed exercise responses and interactive OpenAPI docs.
- Add a non-root Docker image, health check, and Docker Compose setup.
- Add HTTP integration tests. API errors now use FastAPI’s `detail` field.

## 0.1.0 — 2026-10-30

Initial Movement & Exercise Library release.

- Add Python domain, application, infrastructure and presentation modules.
- Add versioned exercise catalog and health API.
- Add Vue library with search, body-area filters and browser-persisted favorites.
- Add guided movement instructions and break timer.
- Add responsive interface and keyboard-accessible dialog.
