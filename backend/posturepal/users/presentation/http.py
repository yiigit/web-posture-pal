import os
import time
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, HTTPException, Request, Response, Query
from pydantic import BaseModel, ConfigDict, Field, field_validator

from posturepal.users.application.accounts import digest_token, hash_password
from posturepal.users.domain.models import User

COOKIE = 'posturepal_session'


class Contract(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)


class Profile(Contract):
    display_name: str = Field(min_length=1, max_length=100)
    bio: str = Field(default='', max_length=1000)
    timezone: str = 'UTC'
    theme: Literal['light', 'dark', 'sportive', 'nike'] = 'light'

    @field_validator('timezone')
    @classmethod
    def valid_timezone(cls, value):
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError):
            raise ValueError('Choose a valid IANA time zone') from None
        return value


class Credentials(BaseModel):
    model_config = ConfigDict(extra='forbid')
    email: str = Field(max_length=254, pattern=r'^[^\s@]+@[^\s@]+\.[^\s@]+$')
    password: str = Field(min_length=12, max_length=128)

    @field_validator('email')
    @classmethod
    def normalize(cls, value):
        return value.lower()


class Registration(Credentials):
    display_name: str = Field(min_length=1, max_length=100)

    @field_validator('display_name')
    @classmethod
    def name(cls, value):
        if not value.strip():
            raise ValueError('Name cannot be blank')
        return value.strip()


class AdminCreate(Registration):
    role: Literal['member', 'admin'] = 'member'


class PasswordChange(BaseModel):
    model_config = ConfigDict(extra='forbid')
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=12, max_length=128)


class PasswordReset(BaseModel):
    model_config = ConfigDict(extra='forbid')
    new_password: str = Field(min_length=12, max_length=128)


class ConfirmPassword(BaseModel):
    password: str = Field(min_length=1, max_length=128)


class Access(Contract):
    role: Literal['member', 'admin']
    active: bool = Field(strict=True)


def current_user_dependency(accounts):
    def current_user(request: Request):
        user = accounts.authenticate(request.cookies.get(COOKIE))
        if user is None:
            raise HTTPException(401, 'Sign in to continue')
        return user
    return current_user


def create_user_router(accounts, require_admin, current_user):
    router = APIRouter(prefix='/api/v1', tags=['Users and profiles'])
    repo = accounts.repository

    def limited(request, action):
        key = action + ':' + (request.client.host if request.client else 'unknown')
        if not repo.attempt(key, int(time.time())):
            raise HTTPException(429, 'Too many attempts. Try again in 15 minutes.', headers={'Retry-After': '900'})

    def handle(operation):
        try:
            return operation()
        except ValueError as error:
            raise HTTPException(409, str(error)) from None
        except LookupError:
            raise HTTPException(404, 'User not found') from None
        except PermissionError as error:
            raise HTTPException(401, str(error)) from None

    def exists(user_id):
        user = repo.get(user_id)
        if user is None:
            raise HTTPException(404, 'User not found')
        return user

    @router.post('/auth/register', response_model=User, status_code=201)
    def register(payload: Registration, request: Request):
        limited(request, 'register')
        return handle(lambda: accounts.create(payload.email, payload.display_name, payload.password))

    @router.post('/auth/login', response_model=User)
    def login(payload: Credentials, request: Request, response: Response):
        limited(request, 'login')
        token, user = handle(lambda: accounts.login(payload.email, payload.password))
        response.set_cookie(COOKIE, token, max_age=43200, httponly=True, samesite='strict',
                            secure=os.getenv('POSTUREPAL_SECURE_COOKIES', 'false').lower() == 'true', path='/')
        return user

    @router.post('/auth/logout', status_code=204)
    def logout(request: Request, response: Response):
        repo.revoke(digest_token(request.cookies.get(COOKIE, '')))
        response.delete_cookie(COOKIE, path='/')

    @router.get('/users/me', response_model=User)
    def me(user: User = Depends(current_user)):
        return user

    @router.put('/users/me', response_model=User)
    def profile(payload: Profile, user: User = Depends(current_user)):
        return repo.profile(user.id, payload.model_dump())

    @router.put('/users/me/password', status_code=204)
    def password(payload: PasswordChange, response: Response, request: Request, user: User = Depends(current_user)):
        limited(request, 'password')
        handle(lambda: accounts.check_password(user, payload.current_password))
        repo.password(user.id, hash_password(payload.new_password))
        response.delete_cookie(COOKIE, path='/')

    @router.delete('/users/me', status_code=204)
    def delete_me(payload: ConfirmPassword, request: Request, response: Response, user: User = Depends(current_user)):
        limited(request, 'password')
        handle(lambda: accounts.check_password(user, payload.password))
        handle(lambda: repo.delete(user.id))
        response.delete_cookie(COOKIE, path='/')

    @router.get('/admin/users', dependencies=[Depends(require_admin)])
    def users(q: str = Query('', max_length=254), limit: int = Query(25, ge=1, le=100), offset: int = Query(0, ge=0)):
        return repo.list(q, limit, offset)

    @router.post('/admin/users', dependencies=[Depends(require_admin)], response_model=User, status_code=201)
    def create(payload: AdminCreate):
        return handle(lambda: accounts.create(payload.email, payload.display_name, payload.password, payload.role))

    @router.get('/admin/users/{user_id}', dependencies=[Depends(require_admin)], response_model=User)
    def detail(user_id: str):
        return exists(user_id)

    @router.put('/admin/users/{user_id}/profile', dependencies=[Depends(require_admin)], response_model=User)
    def admin_profile(user_id: str, payload: Profile):
        exists(user_id)
        return repo.profile(user_id, payload.model_dump())

    @router.put('/admin/users/{user_id}/access', dependencies=[Depends(require_admin)], response_model=User)
    def access(user_id: str, payload: Access):
        return handle(lambda: repo.access(user_id, payload.role, payload.active))

    @router.put('/admin/users/{user_id}/password', dependencies=[Depends(require_admin)], status_code=204)
    def reset(user_id: str, payload: PasswordReset):
        exists(user_id)
        repo.password(user_id, hash_password(payload.new_password))

    @router.delete('/admin/users/{user_id}', dependencies=[Depends(require_admin)], status_code=204)
    def delete(user_id: str):
        handle(lambda: repo.delete(user_id))

    return router
