from datetime import date
from uuid import UUID
from fastapi import APIRouter, Depends, Request, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from posturepal.users.domain.models import User


class HabitChange(BaseModel):
    model_config=ConfigDict(extra='forbid')
    completed: bool=Field(strict=True)


class BreakEvent(BaseModel):
    model_config=ConfigDict(extra='forbid')
    event_id: UUID


def create_activity_router(tracker,current_user):
    router=APIRouter(prefix='/api/v1/me/daily-activity',tags=['Private daily activity'])

    def identity(request:Request,user:User=Depends(current_user)):
        # Prevent a stale browser tab from writing to a newly signed-in account.
        if request.headers.get('X-PosturePal-User')!=user.id:
            raise HTTPException(409,'Your account changed. Reload your activity before continuing.')
        return user

    def call(fn):
        try:return fn()
        except ValueError as error:raise HTTPException(422,str(error)) from None

    @router.get('')
    def export(user:User=Depends(identity)):
        return tracker.export(user.id)

    @router.delete('',status_code=204)
    def delete(user:User=Depends(identity)):
        tracker.delete(user.id)

    @router.get('/{day}')
    def read(day:date,user:User=Depends(identity)):
        return call(lambda:tracker.read(user.id,day))

    @router.put('/{day}/habits/{habit}')
    def habit(day:date,habit:str,payload:HabitChange,user:User=Depends(identity)):
        return call(lambda:tracker.habit(user.id,day,habit,payload.completed))

    @router.post('/{day}/breaks')
    def record(day:date,payload:BreakEvent,user:User=Depends(identity)):
        return call(lambda:tracker.record_break(user.id,day,str(payload.event_id)))

    return router
