"""Single-administrator bearer authentication; no built-in credentials."""
import secrets

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

bearer = HTTPBearer(auto_error=False)


def admin_dependency(token: str):
    def require_admin(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)):
        if len(token) < 32:
            raise HTTPException(503, 'Administration is not configured')
        if credentials is None or not secrets.compare_digest(
            credentials.credentials.encode(), token.encode()
        ):
            raise HTTPException(401, 'Invalid administrator token', headers={'WWW-Authenticate': 'Bearer'})
    return require_admin
