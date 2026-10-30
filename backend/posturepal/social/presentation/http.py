import time
from typing import Literal
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from posturepal.users.domain.models import User


class Privacy(BaseModel):
    model_config=ConfigDict(extra='forbid')
    accept_requests: bool = Field(strict=True)
    sharing_enabled: bool = Field(strict=True)
    default_audience: Literal['private','friends']
    allow_comments: bool = Field(strict=True)


class Activity(BaseModel):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)
    kind: Literal['break','habit','movement','update']
    text: str = Field(min_length=1,max_length=1000)
    audience: Literal['private','friends'] = 'private'


class Audience(BaseModel):
    model_config=ConfigDict(extra='forbid')
    audience: Literal['private','friends']


class Comment(BaseModel):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)
    text: str = Field(min_length=1,max_length=500)


def create_social_router(community,current_user,users):
    router=APIRouter(prefix='/api/v1/social',tags=['Friends and social sharing'])
    def call(fn):
        try: return fn()
        except LookupError as error: raise HTTPException(404,str(error)) from None
        except ValueError as error: raise HTTPException(409,str(error)) from None

    def throttle(uid,action):
        if not users.attempt('social:'+action+':'+uid,int(time.time())):
            raise HTTPException(429,'Too many actions. Try again in 15 minutes.',headers={'Retry-After':'900'})

    @router.get('')
    def overview(offset:int=Query(0,ge=0,le=100000),user:User=Depends(current_user)):
        return community.overview(user.id,offset)

    @router.get('/statistics')
    def statistics(user:User=Depends(current_user)):
        return community.statistics(user.id)

    @router.put('/privacy')
    def privacy(payload:Privacy,user:User=Depends(current_user)):
        return community.privacy(user.id,payload.model_dump())

    @router.post('/friends/{target}',status_code=204)
    def request(target:UUID,user:User=Depends(current_user)):
        throttle(user.id,'request')
        call(lambda:community.request_friend(user.id,str(target)))

    @router.put('/friends/{target}',status_code=204)
    def accept(target:UUID,user:User=Depends(current_user)):
        call(lambda:community.accept(user.id,str(target)))

    @router.delete('/friends/{target}',status_code=204)
    def remove(target:UUID,user:User=Depends(current_user)):
        community.remove(user.id,str(target))

    @router.put('/blocks/{target}',status_code=204)
    def block(target:UUID,user:User=Depends(current_user)):
        call(lambda:community.block(user.id,str(target),True))

    @router.delete('/blocks/{target}',status_code=204)
    def unblock(target:UUID,user:User=Depends(current_user)):
        call(lambda:community.block(user.id,str(target),False))

    @router.post('/activities',status_code=201)
    def publish(payload:Activity,user:User=Depends(current_user)):
        throttle(user.id,'publish')
        return call(lambda:community.publish(user.id,payload.model_dump()))

    @router.get('/activities/{post_id}')
    def post(post_id:UUID,user:User=Depends(current_user)):
        return call(lambda:community.post(user.id,str(post_id)))

    @router.put('/activities/{post_id}',status_code=204)
    def audience(post_id:UUID,payload:Audience,user:User=Depends(current_user)):
        call(lambda:community.edit_post(user.id,str(post_id),payload.audience))

    @router.delete('/activities/{post_id}',status_code=204)
    def delete(post_id:UUID,user:User=Depends(current_user)):
        call(lambda:community.edit_post(user.id,str(post_id)))

    @router.put('/activities/{post_id}/like',status_code=204)
    def like(post_id:UUID,user:User=Depends(current_user)):
        call(lambda:community.like(user.id,str(post_id),True))

    @router.delete('/activities/{post_id}/like',status_code=204)
    def unlike(post_id:UUID,user:User=Depends(current_user)):
        call(lambda:community.like(user.id,str(post_id),False))

    @router.post('/activities/{post_id}/comments',status_code=201)
    def comment(post_id:UUID,payload:Comment,user:User=Depends(current_user)):
        throttle(user.id,'comment')
        call(lambda:community.comment(user.id,str(post_id),payload.text))
        return {'status':'created'}

    @router.delete('/activities/{post_id}/comments/{comment_id}',status_code=204)
    def delete_comment(post_id:UUID,comment_id:UUID,user:User=Depends(current_user)):
        call(lambda:community.delete_comment(user.id,str(post_id),str(comment_id)))

    return router
