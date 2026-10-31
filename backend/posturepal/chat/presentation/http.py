import time
from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, model_validator
from posturepal.chat.domain.coach import CoachUnavailable
from posturepal.users.application.accounts import digest_token


class Message(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    role: Literal['user', 'assistant']
    content: str = Field(min_length=1, max_length=8000)


    @model_validator(mode='after')
    def user_length(self):
        if self.role == 'user' and len(self.content) > 2000:
            raise ValueError('User message must be at most 2000 characters')
        return self


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    consent: bool = Field(strict=True)
    day: date
    messages: list[Message] = Field(min_length=1, max_length=11)

    @model_validator(mode='after')
    def conversation(self):
        if not self.consent:
            raise ValueError('Explicit consent is required before sending chat context')
        if any(message.role != ('user' if index % 2 == 0 else 'assistant')
               for index, message in enumerate(self.messages)) or self.messages[-1].role != 'user':
            raise ValueError('Conversation must alternate user and assistant messages and end with a user message')
        if sum(len(message.content) for message in self.messages) > 12000:
            raise ValueError('Conversation is too long; start a new chat')
        return self


def create_chat_router(coach, current_user, accounts):
    router = APIRouter(prefix='/api/v1/me/coach', tags=['Private AI coach'])

    def identity(request: Request, user=Depends(current_user)):
        if request.headers.get('X-PosturePal-User') != user.id:
            raise HTTPException(409, 'Your account changed. Start a new chat.')
        return user

    @router.get('/context')
    def context(day: date, user=Depends(identity)):
        try:
            return {'enabled': coach.provider.enabled, 'provider': 'OpenAI', 'context': coach.context(user, day)}
        except ValueError as error:
            raise HTTPException(422, str(error)) from None

    @router.post('/messages')
    def message(payload: ChatRequest, request: Request, user=Depends(identity)):
        if not coach.provider.enabled:
            raise HTTPException(503, 'AI coach is not configured. Contact your administrator.')
        # A hashed, expiring request counter contains no conversation or activity data.
        if not accounts.repository.attempt(digest_token('coach:' + user.id), int(time.time())):
            raise HTTPException(429, 'Chat limit reached. Try again in 15 minutes.')
        try:
            reply = coach.reply(user, payload.day, [message.model_dump() for message in payload.messages])
        except ValueError as error:
            raise HTTPException(422, str(error)) from None
        except CoachUnavailable as error:
            raise HTTPException(503, str(error)) from None
        # Do not return an in-flight answer after its session is revoked or changed.
        authenticated = accounts.authenticate(request.cookies.get('posturepal_session'))
        if authenticated is None or authenticated.id != user.id:
            raise HTTPException(401, 'Your session ended. Start a new chat after signing in.')
        return {'reply': reply}

    return router
