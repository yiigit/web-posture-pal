"""Composition root for the FastAPI application."""
import argparse
import asyncio
import logging
from contextlib import asynccontextmanager, suppress
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.responses import JSONResponse
from posturepal.security.admin import bearer
from posturepal.users.infrastructure.repository import UserRepository
from posturepal.users.application.accounts import Accounts
from posturepal.users.presentation.http import create_user_router, current_user_dependency, COOKIE
from posturepal.social.infrastructure.repository import SocialRepository
from posturepal.social.application.community import Community
from posturepal.social.presentation.http import create_social_router
from posturepal.activity.infrastructure.repository import ActivityRepository
from posturepal.activity.application.tracker import ActivityTracker
from posturepal.activity.presentation.http import create_activity_router
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from posturepal.movement.application.library import MovementLibrary
from posturepal.movement.infrastructure.repository import ExerciseRepository
from posturepal.shared.infrastructure.database import Database
from posturepal.security.admin import admin_dependency
from posturepal.breaks.application.coach import BreakCoach
from posturepal.breaks.presentation.http import create_break_router
from posturepal.movement.presentation.http import create_router

class ActivityAccessLogFilter(logging.Filter):
    """Avoid recording habit IDs/dates from private activity request paths."""
    def filter(self, record):
        args = record.args
        return not (isinstance(args,tuple) and len(args)>=3
                    and '/api/v1/me/daily-activity' in str(args[2]))


access_logger=logging.getLogger('uvicorn.access')
if not any(isinstance(item,ActivityAccessLogFilter) for item in access_logger.filters):
    access_logger.addFilter(ActivityAccessLogFilter())


ROOT = Path(__file__).resolve().parents[2]
VERSION = (ROOT / "VERSION").read_text().strip()


class HealthResponse(BaseModel):
    status: str
    version: str


def create_app(database_path: Path | None = None, admin_token: str | None = None, database: Database | None = None) -> FastAPI:
    app = FastAPI(title="PosturePal", version=VERSION)
    database = database or (Database.from_path(database_path) if database_path else Database.configured())
    app.state.database = database
    repository = ExerciseRepository(database)
    token_admin = admin_dependency(admin_token if admin_token is not None else os.getenv('POSTUREPAL_ADMIN_TOKEN', ''))
    accounts = Accounts(UserRepository(database))
    current_user = current_user_dependency(accounts)

    def require_admin(request: Request, credentials=Depends(bearer)):
        if credentials is not None:
            return token_admin(credentials)
        user = accounts.authenticate(request.cookies.get(COOKIE))
        if user is not None:
            if user.role != 'admin':
                raise HTTPException(403, 'Administrator access required')
            return
        return token_admin(None)

    activity = ActivityTracker(ActivityRepository(database))
    activity.repository.purge(activity.today())
    @asynccontextmanager
    async def lifespan(application):
        async def retention_cleanup():
            while True:
                await asyncio.sleep(3600)
                try:
                    await asyncio.to_thread(activity.repository.purge,activity.today())
                except Exception:
                    logging.getLogger(__name__).error('Daily activity retention cleanup failed; retrying next hour')
        task=asyncio.create_task(retention_cleanup())
        try:
            yield
        finally:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task
    app.router.lifespan_context=lifespan
    app.include_router(create_activity_router(activity,current_user))
    app.include_router(create_social_router(Community(SocialRepository(accounts.repository)), current_user, accounts.repository))
    app.include_router(create_user_router(accounts, require_admin, current_user))
    app.include_router(create_router(MovementLibrary(repository), require_admin))

    app.include_router(create_break_router(BreakCoach()))

    @app.middleware('http')
    async def security_headers(request, call_next):
        # A non-simple header prevents cross-origin form submissions from using cookies.
        # No CORS is enabled, so foreign origins cannot send this header in a browser.
        if request.method in {'POST', 'PUT', 'PATCH', 'DELETE'} and (
            request.cookies.get(COOKIE) or request.url.path.startswith('/api/v1/auth/')
        ) and request.headers.get('X-PosturePal-Request') != '1':
            return JSONResponse({'detail': 'Missing request verification header'}, status_code=403)
        response = await call_next(request)
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['Referrer-Policy'] = 'same-origin'
        if request.url.path.startswith('/api/'):
            response.headers['Cache-Control'] = 'no-store'
        return response

    @app.get("/api/v1/health", response_model=HealthResponse, tags=["Health"])
    def health():
        with database.connection() as db:
            db.execute('SELECT 1')
        return HealthResponse(status="ok", version=VERSION)

    # Register before the frontend mount to keep API errors as JSON.
    @app.api_route("/api/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"], include_in_schema=False)
    def unknown_api(path: str):
        raise HTTPException(status_code=404, detail="Route not found")

    app.mount("/", StaticFiles(directory=ROOT / "frontend", html=True), name="frontend")
    return app


app = create_app()


def main():
    import uvicorn

    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args()
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
