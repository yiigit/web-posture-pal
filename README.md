# PosturePal

A smart sitting habit coach, starting with a Movement & Exercise Library. FastAPI backend (Python 3.11+) and Vue 3 frontend. Current release: **0.10.0**.

## Run with Docker

Configure an administrator token first (do not commit `.env`):

```bash
cp .env.example .env
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
```

Paste the generated value after `POSTUREPAL_ADMIN_TOKEN=` in `.env`, then start:

```bash
docker compose up --build -d
```

Open **http://127.0.0.1:8000** for the default dashboard. The movement library is at **http://127.0.0.1:8000/library.html**. Interactive API docs are at **http://127.0.0.1:8000/docs**. Docker Compose builds the Python 3.13 image and runs Uvicorn as a non-root user, with a health check. The port is bound to localhost.

```bash
docker compose logs -f
docker compose down
```

## Run locally

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
# Set a token in this shell (or omit it to disable administration).
export POSTUREPAL_ADMIN_TOKEN="$(.venv/bin/python -c 'import secrets; print(secrets.token_urlsafe(48))')"
PYTHONPATH=backend .venv/bin/python -m posturepal.server
```

Vue 3.5.13 is vendored locally, with no npm build step. Google Fonts is optional and falls back to system fonts. Docker builds and initial Python dependency installation require internet access.

## Included

- Eight gentle movements with steps, duration and seated/standing guidance.
- Body-area filters and case-insensitive search.
- Saved movements persisted in browser localStorage.
- Accessible exercise dialog with start, pause, resume, reset and completion states.
- Responsive layout and reduced-motion support.
- Light, Dark, Sportive, and Nike Orange themes, selectable under Appearance in the header and saved in this browser. Theme preferences work offline; blocked browser storage falls back to an in-memory selection.
- Database-backed exercise CRUD, a secured management screen, and a versioned API with structured errors.

Favorites belong to the current browser. Timers count active page ticks; background tabs can throttle them. Accounts and profiles are supported; there is no webcam monitoring. Daily habit and break completion progress belongs to the current browser.

All pages share persistent left navigation. On narrow screens it becomes an icon rail with accessible link labels.

## Home dashboard

The default start page (`/`) shows today's completed breaks, daily habit progress, catalog size and saved-movement count. Check off habits directly from the dashboard, start a break, open a desk/phone posture check, or explore the movement library. Metrics come from the live catalog and this browser's daily progress; unavailable API data shows an error with retry instead of fabricated counts. The statistics section adds a daily habit completion chart, completed-break total, body-area coverage chart, quick-movement count, average catalog duration and saved-library percentage. Statistics update when habits change or catalog data refreshes; unknown data shows loading/error states. No historical activity or actual workout time is inferred. The protected admin dashboard remains at `/admin.html`.

## Enhanced breaks and daily habits

Open **http://127.0.0.1:8000/breaks.html**, or choose **Breaks & daily habits** in the library sidebar.

- Choose Standard, Pain relief (a gentle comfort break, not treatment), Strength, or Movement habit.
- Read the instructions and start a timed break; pause, resume or reset as needed. Only completed timers increase today's break count.
- Start optional reminders every 20, 30, 45 or 60 minutes. Snooze for five minutes or skip a reminder. Reminders run only while this page is open; background tabs can delay alerts. They are not OS notifications.
- Check your posture in desk or phone-use contexts. These are manual self-checks and reset when you switch context.
- Tick daily movement habits. Habit checkmarks and completed-break counts are saved in localStorage and reset on the next local calendar day. There is no server-side personal health history or account synchronization.

The break timer uses elapsed wall-clock time, so returning from a background tab updates the remaining duration. A paused timer stays paused. Refreshing the page clears active timers and reminders, but keeps today's saved progress. Break routine definitions are a separate coaching module, independent of CRUD-managed exercise catalog entries.

Movement guidance references [NHS sitting exercises](https://www.nhs.uk/live-well/exercise/sitting-exercises/) and [OSHA workstation positions](https://www.osha.gov/etools/computer-workstations/positions). Choose comfortable movements and stop if symptoms worsen.

## Architecture

`backend/posturepal/movement` is the Movement bounded context:

- `domain`: immutable exercise entity and repository interface.
- `application`: library search, retrieval and CRUD use cases.
- `infrastructure`: SQLite repository with parameterized queries and transactional writes; the curated catalog supplies initial seed data only.
- `presentation`: FastAPI router with typed exercise responses.

`backend/posturepal/server.py` composes the dependencies, registers the FastAPI routes and serves the static frontend. Uvicorn runs the ASGI app. `frontend/src/composables/useLibrary.js` owns library state and persistence; `components/MovementFigure.js` is the reusable movement illustration; `main.js` composes the experience. SQLite stores the catalog in `data/posturepal.db` locally and `/app/data/posturepal.db` in Docker. Docker uses the `posturepal-data` named volume. Seed movements are inserted once; deleting all movements does not trigger reseeding. Back up the database before removing volumes. Set `POSTUREPAL_DB_PATH` to override its location.

## Administration and security

Open **http://127.0.0.1:8000/admin.html**, or select **Manage library** in the footer. Sign in with `POSTUREPAL_ADMIN_TOKEN` to open the dashboard with live catalog totals, quick-break counts, duration statistics and body-area/position coverage. Switch to Movements to create, edit or delete exercises. Refresh data retrieves current statistics; saving or deleting a movement also refreshes them. Enter instructions one step per line. The library loads the current database catalog, including updates made in administration.

Accounts use server-side sessions; administrator accounts can also manage the exercise catalog. The existing `POSTUREPAL_ADMIN_TOKEN` remains a bootstrap/recovery credential: use it at `/users.html` to create your first administrator or promote a registered member. Missing/short bootstrap tokens disable token-based administration (503); signed-in administrator accounts still work. Rotate the token and restart the server to revoke token-based access. Local runs read shell environment variables, not `.env` automatically; Docker Compose reads `.env`.

Library reads remain public. Exercise create, update and delete endpoints require an admin session or the bootstrap bearer token, with validation for lengths, allowed areas/illustrations, duration and instructions. Browser input is rendered as text. API responses disable caching; frame embedding is blocked and MIME sniffing is disabled. User sessions use HttpOnly, SameSite=Strict cookies; bootstrap credentials use the Authorization header. Cookie-authenticated writes and auth requests require `X-PosturePal-Request: 1` to prevent cross-origin form submissions. No cross-origin access is enabled.

Use HTTPS when deploying beyond localhost: bearer tokens must not travel over plain HTTP. The Compose configuration binds only to localhost by default. API docs and the static admin page are public, but accessing the page does not authorize mutations.

`backend/posturepal/users` contains account/profile domain models, account use cases, SQLite storage and HTTP contracts.

`backend/posturepal/breaks` is a separate bounded context with domain models, coaching application logic and typed read-only HTTP endpoints. `frontend/src/composables/useDailyHabits.js` owns local daily progress and calendar rollover.

## Friends, sharing and social statistics

Open **`/social.html`**, or use **Friends & sharing** in the sidebar. Sign in with a user account; the bootstrap administrator token does not impersonate a social user.

- **Friends:** exchange your UUID friend code directly, send a request, accept/decline incoming requests, cancel outgoing requests, remove friends or block people. There is no public email directory. Both users must consent before a friendship is active.
- **Activity sharing:** explicitly publish an update, break, habit or movement note. Posts default to **Only me**; choose **Accepted friends** to share. This is self-reported activity, independent of browser-local habit checkmarks and timers. Nothing is auto-published.
- **Engagement:** cheer/uncheer activities and leave comments. Comment authors and activity owners can remove comments. Authors can delete posts or change their audience. The feed is paginated; each activity displays its latest 20 comments.
- **Share links:** use native browser sharing or copy a link. Links do not bypass authentication or post audience checks. Only the owner or permitted accepted friends can open them.
- **Privacy:** control incoming requests, default post audience, friends-only activity visibility and comments. Disabling sharing hides existing friends-only posts immediately; enabling it restores their visibility. Private posts remain private. Removing a friend or blocking immediately revokes access. Unblocking does not recreate friendships.
- **Statistics:** view friends, pending incoming requests, published/shared activities and cheers/comments received on the social Statistics tab. The home dashboard also shows a community summary. These are stored social counts, not verified exercise or health measurements.

User names and activity text are displayed to permitted viewers; email addresses, profile bios and other profile fields are not exposed in the social feed. Social records live in the persistent SQLite database and are removed with account deletion. Publishing, commenting and friend requests are limited to 10 actions per category per 15 minutes per user. Social pages support existing themes and persistent navigation.

### Social API

All `/api/v1/social` endpoints require a signed-in user session; mutation requests also require `X-PosturePal-Request: 1`.

- `GET /social` — feed, friends, privacy and statistics (`offset` paginates the feed)
- `GET /social/statistics`, `PUT /social/privacy`
- `POST/PUT/DELETE /social/friends/{user_id}` — request, accept, remove/decline/cancel
- `PUT/DELETE /social/blocks/{user_id}` — block/unblock
- `POST /social/activities`, `GET/PUT/DELETE /social/activities/{id}`
- `PUT/DELETE /social/activities/{id}/like`
- `POST /social/activities/{id}/comments`, `DELETE /social/activities/{id}/comments/{comment_id}`

Paths above are relative to `/api/v1`. Privacy is checked on every read and engagement request, including direct activity links. Activities outside your audience return 404.

## Users and profiles

Open **`/account.html`** to register, sign in, edit your display name/bio/time zone/preferred theme, change your password, or permanently delete your account. Emails are unique case-insensitively and currently immutable. Profile theme is applied on sign-in/save. The time-zone preference is stored; daily habits still follow the browser's local calendar.

Open **`/users.html`** for administrator user management. Use an admin session or bootstrap token to search/paginate accounts, create members/admins, edit profiles, enable/disable users, assign roles, reset passwords and delete accounts. The last active admin cannot be disabled, demoted or deleted. Bootstrap tokens can always create another admin. Access changes and password changes/resets revoke all sessions for the affected user.

Passwords require 12–128 characters and are salted and hashed with scrypt (`N=16384`, `r=8`, `p=5`). Random session tokens expire after 12 hours and only their SHA-256 digests are stored in SQLite. Logout revokes the current session. Login and registration are throttled per connecting IP (10 attempts per 15 minutes); password confirmations are also throttled. Configure trusted proxy handling carefully if putting multiple clients behind a reverse proxy.

Set **`POSTUREPAL_SECURE_COOKIES=true`** for HTTPS deployments. It defaults to false solely to support local HTTP development. User profile/session tables share the persistent catalog database. Existing installations add these tables automatically without replacing exercise data.

Password recovery is administrator-assisted through `/users.html`; no email delivery, email verification, MFA or self-service reset emails are configured. Daily habits and favorites remain browser-local and are shared by accounts using the same browser; they are not private account-synced health records.

### Account endpoints

- `POST /api/v1/auth/register`, `POST /api/v1/auth/login`, `POST /api/v1/auth/logout`
- `GET/PUT/DELETE /api/v1/users/me`
- `PUT /api/v1/users/me/password`
- `GET/POST /api/v1/admin/users`
- `GET/DELETE /api/v1/admin/users/{id}`
- `PUT /api/v1/admin/users/{id}/profile`, `/access`, `/password`

All browser mutation requests include `X-PosturePal-Request: 1`. Register/login return a public profile, never a password hash or session secret. Session cookies authenticate subsequent same-origin requests. See `/docs` for request schemas.

## API

- `GET /api/v1/breaks` — four guided break routines
- `GET /api/v1/posture-checks` — desk and phone checklists
- `GET /api/v1/daily-habits` — daily movement habit definitions
- `GET /api/v1/health`
- `GET /api/v1/exercises?q=roll&area=Shoulders`
- `GET /api/v1/exercises/neck-release`
- `GET /api/v1/admin/dashboard` — requires bearer token; returns catalog statistics
- `GET /api/v1/admin/session` — requires bearer token
- `POST /api/v1/exercises` — requires bearer token; returns 201, or 409 for duplicate IDs
- `PUT /api/v1/exercises/{id}` — requires bearer token; replaces all editable fields, keeping the ID
- `DELETE /api/v1/exercises/{id}` — requires bearer token; returns 204

Create accepts `id`, `name`, `area`, `duration` (seconds), `description`, `steps` (array), `position`, and `symbol`. Update accepts the same fields except `id`. Supply `Authorization: Bearer <token>` or use Authorize in `/docs`.

Unknown exercises and API routes return HTTP 404 with a JSON `detail` field. OpenAPI is available at `/openapi.json`.

## Verify

```bash
PYTHONPATH=backend .venv/bin/python -m unittest discover -s tests -v
```

## Versioning with Commitizen

Commitizen manages semantic versions through `pyproject.toml` (`project.version`) and synchronizes `VERSION`, the Compose image tag, frontend release labels and the current release line in this README. `VERSION` remains the runtime version file. Changelog history is preserved and new release entries are generated from Conventional Commits.

Install development dependencies and enable the local commit-message hook once per checkout:

```bash
.venv/bin/python -m pip install -r requirements-dev.txt
git config core.hooksPath .githooks
```

Stage changes and use Commitizen's interactive commit command:

```bash
git add <changed-files>
.venv/bin/cz commit
```

Ordinary `git commit` also works with Conventional Commit messages, enforced by the hook. Examples:

- `feat(social): add activity filters` → minor release
- `fix(profile): refresh avatar after sign-in` → patch release
- `docs: clarify Docker setup` or `chore: update tooling` → no automatic release
- `feat!: change the session API` → breaking change (minor while on 0.x)

Run the relevant checks before releasing. Preview, then create the release:

```bash
.venv/bin/cz bump --dry-run --check-consistency
.venv/bin/cz bump --check-consistency
```

The release command updates version files and the changelog, commits the release and creates an annotated `v<version>` tag. Keep the worktree clean before bumping. `major_version_zero = true` keeps releases in 0.x until an explicit stable release decision; switch it off before releasing 1.0.0. Do not edit release numbers individually.

## Git releases

The repository uses the `main` branch and annotated semantic-version tags, starting at `v0.10.0`. Earlier changelog entries describe development milestones and do not have reconstructed Git history. The original initial commit predates Conventional Commit validation; subsequent commits follow Commitizen rules.

Configure your remote before publishing. Push the branch and tags explicitly with `git push -u origin main` and `git push origin --tags`. Environment secrets, local tooling, databases and virtual environments are excluded from Git. Commitizen does not publish remotely.
