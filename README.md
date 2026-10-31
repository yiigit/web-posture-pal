# PosturePal

A smart sitting habit coach, starting with a Movement & Exercise Library. FastAPI backend (Python 3.11+) and Vue 3 frontend. Current release: **0.12.0**.

## Run with Docker

For a new installation, configure an administrator token and separate MySQL application/root passwords (do not commit `.env`). For an existing installation, add the missing MySQL fields to your existing `.env` instead of replacing it:

```bash
cp .env.example .env
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
```

Generate a separate random value for each of `POSTUREPAL_ADMIN_TOKEN`, `MYSQL_PASSWORD`, and `MYSQL_ROOT_PASSWORD` in `.env`, then start:

```bash
docker compose up --build -d
```

Open **http://127.0.0.1:8000** for the default dashboard. The movement library is at **http://127.0.0.1:8000/library.html**. Interactive API docs are at **http://127.0.0.1:8000/docs**. Docker Compose builds the Python 3.13 image and runs Uvicorn as a non-root user, with a health check. The app port is bound to localhost. MySQL 8.4 runs on the internal Compose network with persistent `mysql-data` storage and a non-root application account. It is not exposed on a host port. The app waits for the database health check.

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
# For an external MySQL server, set MYSQL_HOST, MYSQL_PORT, MYSQL_DATABASE,
# MYSQL_USER and MYSQL_PASSWORD in your shell; or use POSTUREPAL_DATABASE_URL.
PYTHONPATH=backend .venv/bin/python -m posturepal.server
```

Vue 3.5.13 is vendored locally, with no npm build step. Fonts use local/system fallbacks with no automatic third-party font requests. Docker builds and initial Python dependency installation require internet access.

## Database configuration

Docker uses MySQL by default. The SQLAlchemy/PyMySQL connection uses `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_DATABASE`, `MYSQL_USER`, and `MYSQL_PASSWORD`. `POSTUREPAL_DATABASE_URL` takes precedence for external connections (`mysql+pymysql://…`, percent-encode credentials when using a URL). Local development without either MySQL configuration or a URL falls back to `POSTUREPAL_DB_PATH` / `data/posturepal.db`; the automated unit suite uses temporary SQLite databases. Passwords are assembled into a SQLAlchemy URL object from separate variables to handle special characters safely. SQL parameters and connection passwords are not logged.

The health endpoint checks database connectivity. Shared SQLAlchemy schema definitions enable foreign-key deletion cascades on both engines. Critical account/rate-limit/friendship changes use explicit transaction locks. New empty databases receive the standard eight-movement catalog once.

### Existing SQLite installations

The old `posturepal-data` Docker volume is retained and mounted read-only at `/legacy`; it is never deleted or overwritten. Migration is explicit and imports exercise data, accounts/password hashes, sessions, privacy settings and social records into an **empty** MySQL application database. Back up your old volume/file first. Stop the old app before importing so the SQLite source is a consistent offline database.

For an existing installation, after configuring MySQL fields, run these commands **before starting the new app**:

```bash
docker compose stop posturepal
docker compose up -d mysql
docker compose build posturepal
docker compose run --rm --no-deps posturepal python -m posturepal.commands.import_sqlite --source /legacy/posturepal.db
docker compose up -d posturepal
```

The importer refuses nonempty destinations and rolls back all copied rows on failure; it does not modify the source. Missing newer tables in an older SQLite file are allowed. Do not seed demo data before importing. For a local SQLite file, mount its containing directory read-only at `/legacy` when running the import command. Existing MySQL data is not automatically merged or replaced.

### Demo data

Set `POSTUREPAL_DEMO_PASSWORD` to a unique 12–128 character password in `.env`, then explicitly run:

```bash
docker compose run --rm posturepal python -m posturepal.commands.seed_demo
```

Sign in at `/account.html` as **`alex@demo.posturepal.test`** using your supplied password. Alex is a demo administrator. Maya, Riley and Jordan use the same supplied demo password with respective emails `maya@demo.posturepal.test`, `riley@demo.posturepal.test`, and `jordan@demo.posturepal.test`; each account receives an independently salted hash.

The demo adds four profiles, two friendships, one incoming friend request, five clearly labeled example activities (including a private post), two cheers and a comment, alongside the standard exercise library. Seeding is transactional and idempotent: rerunning changes no passwords or records. Existing identifier collisions are rejected. It never runs on normal startup and should only be enabled in a development/demo database. Browser-local habits and completed-break counts are not fabricated by the demo seed.

To populate achievement examples separately, after seeding demo accounts, run:

```bash
docker compose run --rm posturepal python -m posturepal.commands.seed_achievements
```

This explicitly creates **synthetic** private activity history: Alex has 30 active days and all six awards; Maya has seven days with partial trophy progress; Riley has one habit checked; Jordan remains empty. Sign in to each demo account to view its dashboard or breaks page. This is sample history, not measured activity. Use only in a development/demo database. It never runs at startup, changes real accounts, publishes posts, or touches browser-local activity. It refuses existing activity in any target account and is transactional and idempotent. Deleted sample history is not recreated on reruns. The usual export, erasure and 90-day retention rules apply; samples naturally age out.


## Included

- Eight gentle movements with steps, duration and seated/standing guidance.
- Body-area filters and case-insensitive search.
- Saved movements persisted in browser localStorage.
- Accessible exercise dialog with start, pause, resume, reset and completion states.
- Responsive layout and reduced-motion support.
- Light, Dark, Sportive, and Nike Orange themes, selectable under Appearance in the header and saved in this browser. Theme preferences work offline; blocked browser storage falls back to an in-memory selection.
- Database-backed exercise CRUD, a secured management screen, and a versioned API with structured errors.

Favorites remain browser-local. Guest daily habits and break counts remain in the browser; signed-in users save daily activity privately to their account. Accounts and profiles are supported; there is no webcam monitoring.

All pages share persistent left navigation. Administration and User management links appear only for an active, signed-in administrator; guest and member sessions do not see these links. On narrow screens it becomes an icon rail with accessible link labels.

## Home dashboard

The default start page (`/`) shows today's completed breaks, daily habit progress, catalog size and saved-movement count. Check off habits directly from the dashboard, start a break, open a desk/phone posture check, or explore the movement library. Metrics come from the live catalog and private account activity when signed in, or guest browser progress otherwise; unavailable API data shows an error with retry instead of fabricated counts. The statistics section adds a daily habit completion chart, completed-break total, body-area coverage chart, quick-movement count, average catalog duration and saved-library percentage. Statistics update when habits change or catalog data refreshes; unknown data shows loading/error states. No historical activity or actual workout time is inferred. The protected admin dashboard remains at `/admin.html`.

## Enhanced breaks and daily habits

Open **http://127.0.0.1:8000/breaks.html**, or choose **Breaks & daily habits** in the library sidebar.

- Choose Standard, Pain relief (a gentle comfort break, not treatment), Strength, or Movement habit.
- Read the instructions and start a timed break; pause, resume or reset as needed. Only completed timers increase today's break count.
- Start optional reminders every 20, 30, 45 or 60 minutes. Snooze for five minutes or skip a reminder. Reminders run only while this page is open; background tabs can delay alerts. They are not OS notifications.
- Check your posture in desk or phone-use contexts. These are manual self-checks and reset when you switch context.
- Tick daily movement habits. Guests keep the current local day in the browser. Signed-in users save private daily aggregates to their account for 90 days, synchronized across devices. A new local day starts a fresh checklist. No guest history is automatically uploaded, and daily activity is never shared automatically.

The break timer uses elapsed wall-clock time, so returning from a background tab updates the remaining duration. A paused timer stays paused. Refreshing the page clears active timers and reminders, but retrieves today's activity from the appropriate guest/account store. Break routine definitions are a separate coaching module, independent of CRUD-managed exercise catalog entries.

Movement guidance references [NHS sitting exercises](https://www.nhs.uk/live-well/exercise/sitting-exercises/) and [OSHA workstation positions](https://www.osha.gov/etools/computer-workstations/positions). Choose comfortable movements and stop if symptoms worsen.

## Architecture

`backend/posturepal/movement` is the Movement bounded context:

- `domain`: immutable exercise entity and repository interface.
- `application`: library search, retrieval and CRUD use cases.
- `infrastructure`: portable SQLAlchemy repository with parameterized queries and transactional writes; the curated catalog supplies initial seed data only.
- `presentation`: FastAPI router with typed exercise responses.

`backend/posturepal/server.py` composes the dependencies, registers the FastAPI routes and serves the static frontend. Uvicorn runs the ASGI app. `frontend/src/composables/useLibrary.js` owns library state and persistence; `components/MovementFigure.js` is the reusable movement illustration; `main.js` composes the experience. MySQL stores catalog, account and social data in Docker's `mysql-data` named volume. Schema and connection handling live in `shared/infrastructure/database.py`. Seed movements are inserted once; deleting all movements does not trigger reseeding. Back up data before removing volumes. SQLite remains available for isolated tests and local development compatibility.

## Administration and security

Open **http://127.0.0.1:8000/admin.html**, or select **Manage library** in the footer. Sign in with `POSTUREPAL_ADMIN_TOKEN` to open the dashboard with live catalog totals, quick-break counts, duration statistics and body-area/position coverage. Switch to Movements to create, edit or delete exercises. Refresh data retrieves current statistics; saving or deleting a movement also refreshes them. Enter instructions one step per line. The library loads the current database catalog, including updates made in administration.

Accounts use server-side sessions; administrator accounts can also manage the exercise catalog. The existing `POSTUREPAL_ADMIN_TOKEN` remains a bootstrap/recovery credential: use it at `/users.html` to create your first administrator or promote a registered member. Missing/short bootstrap tokens disable token-based administration (503); signed-in administrator accounts still work. Rotate the token and restart the server to revoke token-based access. Local runs read shell environment variables, not `.env` automatically; Docker Compose reads `.env`.

Library reads remain public. Exercise create, update and delete endpoints require an admin session or the bootstrap bearer token, with validation for lengths, allowed areas/illustrations, duration and instructions. Browser input is rendered as text. API responses disable caching; frame embedding is blocked and MIME sniffing is disabled. User sessions use HttpOnly, SameSite=Strict cookies; bootstrap credentials use the Authorization header. Cookie-authenticated writes and auth requests require `X-PosturePal-Request: 1` to prevent cross-origin form submissions. No cross-origin access is enabled.

Use HTTPS when deploying beyond localhost: bearer tokens must not travel over plain HTTP. The Compose configuration binds only to localhost by default. API docs and the static admin page are public, but accessing the page does not authorize mutations.

`backend/posturepal/users` contains account/profile domain models, account use cases, SQLAlchemy-backed storage and HTTP contracts.

`backend/posturepal/breaks` is a separate bounded context with domain models, coaching application logic and typed read-only HTTP endpoints. `frontend/src/composables/useDailyHabits.js` owns local daily progress and calendar rollover.

## Achievements, progress and motivation

The dashboard and breaks page include an Achievements & momentum panel with badges, trophies, levels, motivational feedback and a 7/30-day activity grid. Signed-in progress is computed privately from the retained 90-day activity window. Guest badges are calculated entirely in the browser from today's local progress; no guest activity is sent to this API.

- Badges: first recorded break, first checked habit, and a day with all four habits checked.
- Trophies: ten recorded breaks, seven active days, and thirty active days. Active days need not be consecutive; rest days carry no penalty.
- Points: 10 per active day, 5 per habit checkmark, and 10 per break for up to three breaks each day. Each 100 points advances a level. Extra breaks still count toward recorded totals but do not create unlimited daily points.
- Updates: local saves are reactive; visible signed-in pages poll every 15 seconds for cross-tab/device changes. This is near-real-time refresh, not sensor monitoring or server push. Hidden tabs pause polling.
- Privacy: no leaderboard, automatic social publication or separate permanent award ledger. Awards/points may change when habits are unchecked, activity is erased, or older records expire. These are self-reported wellbeing actions, not verified workout/medical outcomes.

Own-account endpoint: `GET /api/v1/me/daily-activity/progress?day=YYYY-MM-DD&days=7` (up to 30 display days). It requires the existing session and matching `X-PosturePal-User` header. Progress remains inaccessible to friends and bootstrap admin tokens.

## Daily activity privacy

Signed-in users save habit checkmarks and completed-break counts to their own accounts; guests record only in browser storage. `/account.html` has daily activity export and deletion controls. `/privacy.html` explains the user-facing behavior. A 90-day retention window applies to server-side activity, with startup/hourly cleanup. No automatic social publication or guest-to-account history upload occurs. Account deletion cascades to activity records.

Endpoints (own session only; mutations also require the existing CSRF header, and all requests require `X-PosturePal-User` matching the signed-in user ID):

- `GET/DELETE /api/v1/me/daily-activity` — export retained activity / delete activity history
- `GET /api/v1/me/daily-activity/{YYYY-MM-DD}` — read a daily aggregate
- `PUT /api/v1/me/daily-activity/{YYYY-MM-DD}/habits/{id}` — set a validated habit's completed flag
- `POST /api/v1/me/daily-activity/{YYYY-MM-DD}/breaks` — record an idempotent UUID break event

See [PRIVACY.md](PRIVACY.md) for the safeguards, retention boundaries and GDPR/HIPAA deployment obligations. These features do not certify compliance. Encryption, backup retention, broader data-subject request handling, audits and applicable legal/organizational measures remain operator responsibilities.

Client storage isolation can be tested with Node 22 (not required to run the app):

```bash
node --test tests/daily_activity.test.mjs
```

## Friends, sharing and social statistics

Open **`/social.html`**, or use **Friends & sharing** in the sidebar. Sign in with a user account; the bootstrap administrator token does not impersonate a social user.

- **Friends:** exchange your UUID friend code directly, send a request, accept/decline incoming requests, cancel outgoing requests, remove friends or block people. There is no public email directory. Both users must consent before a friendship is active.
- **Activity sharing:** explicitly publish an update, break, habit or movement note. Posts default to **Only me**; choose **Accepted friends** to share. This is self-reported activity, independent of browser-local habit checkmarks and timers. Nothing is auto-published.
- **Engagement:** cheer/uncheer activities and leave comments. Comment authors and activity owners can remove comments. Authors can delete posts or change their audience. The feed is paginated; each activity displays its latest 20 comments.
- **Share links:** use native browser sharing or copy a link. Links do not bypass authentication or post audience checks. Only the owner or permitted accepted friends can open them.
- **Privacy:** control incoming requests, default post audience, friends-only activity visibility and comments. Disabling sharing hides existing friends-only posts immediately; enabling it restores their visibility. Private posts remain private. Removing a friend or blocking immediately revokes access. Unblocking does not recreate friendships.
- **Statistics:** view friends, pending incoming requests, published/shared activities and cheers/comments received on the social Statistics tab. The home dashboard also shows a community summary. These are stored social counts, not verified exercise or health measurements.

User names and activity text are displayed to permitted viewers; email addresses, profile bios and other profile fields are not exposed in the social feed. Social records live in the persistent application database and are removed with account deletion. Publishing, commenting and friend requests are limited to 10 actions per category per 15 minutes per user. Social pages support existing themes and persistent navigation.

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

Passwords require 12–128 characters and are salted and hashed with scrypt (`N=16384`, `r=8`, `p=5`). Random session tokens expire after 12 hours and only their SHA-256 digests are stored in the application database. Logout revokes the current session. Login and registration are throttled per connecting IP (10 attempts per 15 minutes); password confirmations are also throttled. Configure trusted proxy handling carefully if putting multiple clients behind a reverse proxy.

Set **`POSTUREPAL_SECURE_COOKIES=true`** for HTTPS deployments. It defaults to false solely to support local HTTP development. User profile/session tables share the persistent catalog database. Existing installations add these tables automatically without replacing exercise data.

Password recovery is administrator-assisted through `/users.html`; no email delivery, email verification, MFA or self-service reset emails are configured. Favorites remain browser-local. Daily activity is private account data when signed in, and browser-local guest data otherwise. Server saves never fall back to guest storage on network/authentication errors. Account activity is not automatically imported from guest history.

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

The MySQL integration smoke test requires a disposable database whose name ends in `_test` (it drops only that explicitly selected database's application tables):

```bash
# Set POSTUREPAL_TEST_MYSQL_URL securely in the test shell.
PYTHONPATH=backend .venv/bin/python tests/mysql_smoke.py
```

It validates SQLite import, demo idempotency, MySQL CRUD, Unicode profiles, account roles, social privacy and deletion cascades. Never point it at application data.

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
.venv/bin/python scripts/release.py prepare 0.13.0  # choose the intended version
```

The release command updates version files and the changelog, commits the release and creates an annotated `v<version>` tag. Keep the worktree clean before bumping. `major_version_zero = true` keeps releases in 0.x until an explicit stable release decision; switch it off before releasing 1.0.0. Do not edit release numbers individually.

## Git releases

The repository uses `main` and `develop` branches and annotated semantic-version tags, starting at `v0.10.0`. Earlier changelog entries describe development milestones and do not have reconstructed Git history. The original initial commit predates Conventional Commit validation; subsequent commits follow Commitizen rules.

Configure your remote before publishing. Push the branch and tags explicitly with `git push -u origin main` and `git push origin --tags`. Environment secrets, local tooling, databases and virtual environments are excluded from Git. Commitizen does not publish remotely.


## Private AI coach

Open `/coach.html` or **AI coach** in the shared navigation. Sign-in is required. The page previews the exact account context and requires explicit consent before each new conversation sends anything to OpenAI. Ask about your profile, daily activity, progress, achievements or motivation. Answers are general habit guidance and may be incorrect; they are not diagnosis or treatment.

Configure these server-side variables in your environment (or your local `.env` for Docker), then rebuild/restart the app:

```dotenv
OPENAI_API_KEY=
POSTUREPAL_AI_MODEL=
```

Supply your own OpenAI API key and a Responses-compatible text model ID available to your API project. Both are required; otherwise the page explains that chat is unavailable. No key is sent to the frontend, and there is no simulated AI fallback. Configure provider spending limits separately.

```bash
docker compose up --build -d --no-deps posturepal
```

Each send includes only the authenticated user's display name, time zone, retained aggregate activity totals, points/level, derived awards and last seven calendar days of activity, plus at most five prior exchanges in the current page. Email, bio, friends, passwords, administrator tokens and guest activity are excluded. Context is rebuilt on every send and never accepted from the browser. The client permits five exchanges per chat; clear it to start again. There is a server-side limit of ten requests per account per 15-minute window, bounded input/output and a 30-second upstream timeout. Failed attempts can consume that limit.

Chat has no tools, social publishing or record-changing capabilities. Conversations are not stored in the application database or browser storage. Clearing chat, leaving/reloading the page, or detecting an account/session change clears its in-memory state and consent. Clearing the page cannot cancel provider processing already begun or erase provider logs. Only hashed, expiring rate counters persist, using the existing throttle infrastructure. Account changes are checked on focus, browser account-change events and every 15 seconds while visible; stale in-flight responses are discarded. Protected APIs continue to enforce session ownership and CSRF checks.

The integration uses the [OpenAI Responses API](https://developers.openai.com/api/reference/python/resources/responses/methods/create) with `store: false`, without provider conversations or previous-response IDs. This disables response retrieval storage; it is not a promise of zero provider retention. Operators must review provider policies, contracts, data residency, consent/legal basis and regulated-data eligibility before enabling external AI. See [PRIVACY.md](PRIVACY.md). A live provider request is not part of automated tests; tests inject a fake provider and never transmit real profile/activity data.


If the coach reports that the configured model is unavailable, OpenAI returned `model_not_found`: check the exact `POSTUREPAL_AI_MODEL` ID and that the API project can access it. After saving any local environment change, recreate the app container with `docker compose up -d --no-deps posturepal`. A ChatGPT subscription does not configure the API project. The coach distinguishes model access, API-key authentication, permissions, billing/quota, rate limits, network failures and incomplete responses using safe fixed messages; raw provider errors are never shown. See [OpenAI error codes](https://developers.openai.com/api/docs/guides/error-codes).


## GitHub Actions and releases

Two workflows live in `.github/workflows`:

- **CI** runs on pull requests and pushes to `main`/`develop`. It checks version consistency, runs Python tests on 3.11 and 3.13, runs Node 22 client privacy tests, validates against an isolated MySQL 8.4 database, and builds/starts the Docker image. CI uses temporary test data and mocked AI responses; it needs no application secrets or real OpenAI key.
- **Release** runs on pushed `v*` tags or manually through **Actions → Release → Run workflow**. Choose `main` or `develop` and enter the intended stable version without `v`. It first runs the complete CI workflow. Commitizen then synchronizes versions, moves the detailed Unreleased notes into the selected release, preserves historical notes, creates the release commit and annotated tag, pushes that branch/tag atomically, and creates a GitHub Release from those notes. Existing GitHub Releases are left unchanged.

The workflows pin official checkout/setup actions to verified commit hashes. CI has read-only repository permissions; only the publication job receives `contents: write`. Releases serialize to prevent concurrent tag creation. No production database, deployment or container registry publishing is performed.

Before a manual release, add meaningful notes under **Unreleased**, commit the changes and push the selected branch. Use the repository's **Actions** settings to permit GitHub Actions and the publication job's write permission. Branch/tag protection must permit the release bot to push, or maintainers must create the release locally and push its branch/tag themselves. The workflow never force-pushes or bypasses protection rules. Manual dispatch becomes available after the workflow exists on the repository's default branch.

For local preparation, with a clean checkout and development dependencies installed:

```bash
.venv/bin/python scripts/release.py verify
# Replace the example with the intended next version:
.venv/bin/python scripts/release.py prepare 0.13.0
.venv/bin/python scripts/release.py verify --tag v0.13.0
```

The helper wraps Commitizen and preserves curated Unreleased notes through `.github/release-notes.md.j2`. It keeps an empty Unreleased section separate from numbered releases and rejects stale version references, duplicate release headings, downgrades, non-annotated/mismatched tags, dirty worktrees and missing release notes. Only stable `major.minor.patch` versions are currently supported. It does not push or publish by itself. Use `python scripts/release.py notes --output release-notes.md` to export the current release notes outside automated publication.

Pushing an annotated version tag whose commit contains these workflow files runs validation and publishes its GitHub Release without a second bump. For a failed manual publication, rerun the same version only while that release commit is still the selected branch's HEAD; the helper verifies the existing tag and skips the bump. If newer commits have landed, publish from the original version tag instead, provided that commit contains the workflows; older tags can be published manually through GitHub Releases. Manual releases publish within the same workflow because pushes made with `GITHUB_TOKEN` do not trigger another tag workflow. GitHub Releases can also be created manually from a verified existing tag after checks pass.

These files must be committed and pushed before GitHub can execute them. Local workflow syntax/release-helper checks cannot establish that repository permissions and protection rules allow publication. See [GitHub workflow permissions](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#permissions).
