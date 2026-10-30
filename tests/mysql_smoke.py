"""Integration validation against a disposable MySQL database ending in _test.

POSTUREPAL_TEST_MYSQL_URL is supplied by the test operator, never committed.
Run: PYTHONPATH=backend .venv/bin/python tests/mysql_smoke.py
"""
import os
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory
from fastapi.testclient import TestClient
from sqlalchemy.engine import make_url
from posturepal.shared.infrastructure.database import Database, schema
from posturepal.commands.seed_demo import seed_demo, demo_id
from posturepal.commands.import_sqlite import import_sqlite
from posturepal.server import create_app
from posturepal.users.infrastructure.repository import UserRepository
from posturepal.users.application.accounts import Accounts
from posturepal.movement.infrastructure.repository import ExerciseRepository


def validate(url):
    if not make_url(url).database.endswith('_test'):
        raise ValueError('Use a disposable database whose name ends in _test')
    database=Database(url)
    password='isolated demo password 123'
    token='isolated-admin-token-'+'x'*40
    try:
        # Clean only this explicitly designated test database.
        schema.drop_all(database.engine)
        database.engine.dispose()
        database=Database(url)
        with TemporaryDirectory() as directory:
            source=Path(directory)/'old.db'
            old=Database.from_path(source)
            exercises=ExerciseRepository(old)
            accounts=Accounts(UserRepository(old))
            accounts.create('legacy@example.test','Legacy user',password)
            original_count=len(exercises.all())
            old.engine.dispose()
            assert import_sqlite(source,database)>0
            assert len(ExerciseRepository(database).all())==original_count
            assert UserRepository(database).credentials('legacy@example.test')
            try: import_sqlite(source,database)
            except ValueError: pass
            else: raise AssertionError('Import overwrote existing data')
        assert seed_demo(database,password)['seeded']
        assert not seed_demo(database,'another unique password')['seeded']
        app=create_app(admin_token=token,database=database)
        with TestClient(app) as client:
            client.headers['X-PosturePal-Request']='1'
            assert client.get('/api/v1/health').status_code==200
            assert client.get('/api/v1/social').status_code==401
            response=client.post('/api/v1/auth/login',json={'email':'alex@demo.posturepal.test','password':password})
            assert response.status_code==200,response.text
            assert response.json()['role']=='admin'
            client.headers['X-PosturePal-User']=response.json()['id']
            from datetime import datetime,timezone
            from uuid import uuid4
            activity_path='/api/v1/me/daily-activity/'+datetime.now(timezone.utc).date().isoformat()
            event={'event_id':str(uuid4())}
            assert client.put(activity_path+'/habits/desk-check',json={'completed':True}).status_code==200
            assert client.post(activity_path+'/breaks',json=event).json()['breaks']==1
            assert client.post(activity_path+'/breaks',json=event).json()['breaks']==1
            assert len(client.get('/api/v1/me/daily-activity').json()['daily_activity'])==1
            progress=client.get('/api/v1/me/daily-activity/progress?day='+datetime.now(timezone.utc).date().isoformat()).json()
            assert progress['totals']['breaks']==1
            assert any(award['id']=='first-break' and award['earned'] for award in progress['awards'])
            assert client.delete('/api/v1/me/daily-activity').status_code==204
            assert client.get(activity_path).json()['breaks']==0
            stats=client.get('/api/v1/social/statistics').json()
            assert stats['friends']==2 and stats['likes_received']==2 and stats['comments_received']==1,stats
            assert client.get('/api/v1/admin/users?q=demo').json()['total']==4
            profile={'display_name':'Alex Test','bio':'Unicode test 🌱','timezone':'Europe/Brussels','theme':'dark'}
            assert client.put('/api/v1/users/me',json=profile).status_code==200
            payload={'id':'mysql-test','name':'Test','area':'Back','duration':60,'description':'Test exercise','steps':['Move gently'],'position':'Seated','symbol':'twist'}
            assert client.post('/api/v1/exercises',json=payload).status_code==201
            assert client.post('/api/v1/exercises',json=payload).status_code==409
            update={k:v for k,v in payload.items() if k!='id'}
            assert client.put('/api/v1/exercises/mysql-test',json=update).status_code==200
            assert client.delete('/api/v1/exercises/mysql-test').status_code==204
            assert client.get('/api/v1/admin/dashboard').status_code==200
            assert client.post('/api/v1/social/activities',json={'kind':'update','text':'Private test'}).status_code==201
            settings=client.get('/api/v1/social').json()['privacy']
            assert client.put('/api/v1/social/privacy',json={**settings,'allow_comments':False}).status_code==200
            assert client.put('/api/v1/social/blocks/'+demo_id('maya')).status_code==204
            assert client.get('/api/v1/social/statistics').json()['friends']==1
            assert client.post('/api/v1/auth/logout').status_code==204
            assert client.post('/api/v1/auth/login',json={'email':'maya@demo.posturepal.test','password':password}).status_code==200
            assert client.get('/api/v1/admin/users').status_code==403
            assert client.get(activity_path).status_code==409
            client.headers['X-PosturePal-User']=demo_id('maya')
            assert client.get(activity_path).json()['habits']==[]
            feed=client.get('/api/v1/social').json()['feed']['items']
            assert all(post['user_id']!=demo_id('alex') for post in feed)
        print('PASS: MySQL migration, demo idempotency, authentication, Unicode profiles, CRUD, private daily activity, privacy, social statistics and blocking')
    finally:
        schema.drop_all(database.engine)
        database.engine.dispose()


if __name__=='__main__':
    validate(os.environ['POSTUREPAL_TEST_MYSQL_URL'])
