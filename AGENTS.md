# PosturePal agent guide

## Scope and working practices

These instructions apply throughout this repository. Read `README.md` and relevant source before changing behavior. Keep changes focused on the user's request, preserve their edits, and report what changed, validation performed, and any remaining verification limits. Do not introduce new frameworks or dependencies without a concrete need.

## Stack and architecture

- Backend: Python 3.11+, FastAPI and Uvicorn. Docker uses Python 3.13.
- Frontend: Vue 3 native ES modules, using the vendored runtime in `frontend/vendor`. There is no Node/npm build step.
- Persistence: MySQL 8.4 in Docker (`mysql-data` volume), through SQLAlchemy/PyMySQL. Shared schema and transaction adapters live in `shared/infrastructure/database.py`. Temporary SQLite databases remain supported for isolated tests; unconfigured local runs retain the SQLite development fallback.
- `backend/posturepal/server.py` is the composition root and serves the API and static frontend.
- Bounded contexts: `movement`, `breaks`, `users`, `social`, and `activity`, each with domain, application, infrastructure and presentation modules where applicable.
- Keep domain rules independent of FastAPI and storage details. Put use cases in application modules, database operations in infrastructure, and request validation/authentication adapters in presentation.
- Use parameterized SQL, explicit transactions where atomicity matters, and close database connections. Schema changes must preserve existing catalog, account and social data. Seed the exercise catalog only once.
- Reuse Vue components and composables. Shared navigation lives in `AppSidebar.js`, profile access in `ProfileBadge.js`, and palette tokens in `themes.css`.

## Routes and UI conventions

- `/`: default wellbeing dashboard.
- `/library.html`: CRUD-backed movement library.
- `/breaks.html`: guided breaks, reminders, posture checks and daily habits.
- `/account.html`: registration, sign-in and profile management.
- `/admin.html`: secured catalog dashboard and management.
- `/users.html`: secured user management.
- `/social.html`: friends, sharing, privacy and social statistics.
- Keep the shared left navigation visible on all pages, including a compact rail on narrow screens. Show profile access at the top.
- Support Light, Dark, Sportive and orange themes through shared tokens. Do not add Nike logos or swooshes.
- Preserve keyboard access, accessible control names, focus states, responsive layouts and reduced-motion preferences. Render user text through Vue interpolation; do not use raw HTML rendering for user content.
- Guest habits/break counts are browser-local; signed-in daily activity is private account data. Never auto-import guest history, cache account activity in guest storage, or reassign events after account switching. Favorites remain browser-local. Do not imply verified workout measurements.
- Retain daily activity export/erasure controls, ownership checks, bounded retention and separation from social sharing. Review PRIVACY.md; do not claim GDPR/HIPAA certification from code features alone.
- Do not automatically publish activities. Social posts default to private and may be shared with accepted friends explicitly. Never bypass audience checks for direct links, reactions, comments or statistics.

## Security and secrets

- Never read, print, commit or bake actual `.env` contents, credentials, session tokens or databases into artifacts. Document configuration through `.env.example` with empty placeholders.
- Retain authentication and authorization for all protected mutations. Bootstrap admin tokens and signed-in admin sessions have different purposes; bootstrap tokens must not impersonate social users.
- User sessions are server-side, expiring and revocable. Keep passwords salted/hashed and session secrets hashed at rest; never return either in API responses.
- Preserve the `X-PosturePal-Request: 1` requirement for auth requests and cookie-authenticated writes, HttpOnly/SameSite cookies, authentication throttling, and immediate access revocation after password/access changes.
- Use `POSTUREPAL_SECURE_COOKIES=true` for HTTPS deployment. The false default supports localhost development only.
- Maintain last-active-admin protection and account-deletion cascades. Check both ownership and visibility for social operations; unfriending, blocking and privacy changes must revoke access.
- Demo seeding is opt-in through `python -m posturepal.commands.seed_demo`, requires an explicit `POSTUREPAL_DEMO_PASSWORD`, and must be idempotent. Never invent personal progress or auto-seed demo accounts on startup.
- SQLite import is explicit, read-only at the source, transactional at the MySQL destination, and refuses a nonempty destination. Preserve the old `posturepal-data` volume.
- Do not disable security controls or weaken tests to make checks pass. Do not remove persistent Docker volumes unless explicitly requested.

## Setup and commands

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
git config core.hooksPath .githooks
```

Local server (reads shell environment, not `.env` automatically):

```bash
PYTHONPATH=backend .venv/bin/python -m posturepal.server
```

Docker (requires configured `.env`; see `.env.example`):

```bash
docker compose up --build -d
docker compose logs -f
docker compose down
```

Do not run `docker compose config` without `--quiet` against real credentials: expanded configuration can disclose secrets.

## Validation

Run relevant tests for the change; run the full suite for authentication, authorization, persistence or shared API changes:

```bash
PYTHONPATH=backend .venv/bin/python -m unittest discover -s tests -v
```

For MySQL-specific changes, run `tests/mysql_smoke.py` against a disposable MySQL database ending in `_test`, configured through `POSTUREPAL_TEST_MYSQL_URL`. That test removes application tables in the selected test database. Never run it against live data.

Tests should use temporary databases and isolated sessions, not real user data. Cover unauthorized access, invalid input, ownership and privacy restrictions, persistence, and relevant success paths. For UI changes, verify affected pages, theme variants, keyboard controls and narrow-screen layouts when browser tooling is available. Static structure checks do not establish that browser interactions work. Clearly report when browser verification or Docker builds could not run.

## Git and releases

- Use Conventional Commits, checked by the `.githooks/commit-msg` hook. Examples: `feat(social): add feed filters`, `fix(auth): revoke expired sessions`, `docs: update setup guidance`.
- Use Commitizen; do not manually edit release numbers or fabricate historical tags.
- `pyproject.toml` (`project.version`) is the release source of truth. Commitizen synchronizes runtime `VERSION`, Compose image tag, frontend release labels and the README current-version line.
- Commitizen maintains `CHANGELOG.md`, release commits and annotated `v<version>` tags. Preserve existing changelog history.
- Tooling and documentation-only changes do not require a version bump. Features produce minor releases and fixes produce patches; breaking changes remain minor while `major_version_zero = true`.

```bash
.venv/bin/cz commit
.venv/bin/cz bump --dry-run --check-consistency
# Only when a release is requested/authorized, after checks and with a clean worktree:
.venv/bin/cz bump --check-consistency
```

Do not push branches/tags or publish remotely without authorization. Keep environment secrets, virtual environments, local tooling and runtime data out of Git.
