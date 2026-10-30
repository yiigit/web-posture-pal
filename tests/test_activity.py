import unittest
from datetime import datetime,timezone,timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from fastapi.testclient import TestClient
from posturepal.server import create_app
from posturepal.activity.infrastructure.repository import ActivityRepository
from posturepal.activity.application.tracker import ActivityTracker
from posturepal.users.application.accounts import Accounts
from posturepal.users.infrastructure.repository import UserRepository
from uuid import uuid4


class ActivityTests(unittest.TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/'activity.db'
        self.app=create_app(self.path,'test-admin-'+'x'*40)
        accounts=Accounts(UserRepository(self.app.state.database))
        self.clients=[];self.users=[]
        for name in ['alice','bob']:
            user=accounts.create(name+'@example.test',name,'a strong private password')
            client=TestClient(self.app)
            client.headers['X-PosturePal-Request']='1'
            client.post('/api/v1/auth/login',json={'email':user.email,'password':'a strong private password'})
            client.headers['X-PosturePal-User']=user.id
            self.clients.append(client);self.users.append(user)
            self.addCleanup(client.close)
        self.a,self.b=self.clients
        self.day=datetime.now(timezone.utc).date().isoformat()
        self.base='/api/v1/me/daily-activity'

    def test_guests_cannot_store_or_read_activity(self):
        with TestClient(self.app) as guest:
            for method,path,data in [('GET',self.base,None),('GET',self.base+'/'+self.day,None),('PUT',self.base+'/'+self.day+'/habits/first-task',{'completed':True}),('POST',self.base+'/'+self.day+'/breaks',{'event_id':str(uuid4())}),('DELETE',self.base,None)]:
                self.assertEqual(guest.request(method,path,json=data).status_code,401)
        with self.app.state.database.connection() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM daily_activity').fetchone()[0],0)

    def test_activity_is_owned_and_not_social(self):
        path=self.base+'/'+self.day
        response=self.a.put(path+'/habits/first-task',json={'completed':True})
        self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(response.json()['habits'],['first-task'])
        self.assertEqual(self.b.get(path).json()['habits'],[])
        self.assertEqual(self.a.get('/api/v1/social/statistics').json()['activities'],0)
        self.assertEqual(self.b.get(self.base,headers={'X-PosturePal-User':self.users[0].id}).status_code,409)
        self.assertEqual(self.a.put(path+'/habits/desk-check',json={'completed':True,'user_id':self.users[1].id}).status_code,422)
        self.assertEqual(self.a.put(path+'/habits/nonexistent',json={'completed':True}).status_code,422)
        with TestClient(create_app(self.path,'test-admin-'+'x'*40)) as restarted:
            restarted.cookies.update(self.a.cookies)
            self.assertEqual(restarted.get(path,headers={'X-PosturePal-User':self.users[0].id}).json()['habits'],['first-task'])

    def test_break_retry_is_idempotent_and_changes_are_independent(self):
        path=self.base+'/'+self.day
        event={'event_id':str(uuid4())}
        for _ in range(2):
            response=self.a.post(path+'/breaks',json=event)
            self.assertEqual(response.status_code,200,response.text)
            self.assertEqual(response.json()['breaks'],1)
        self.a.put(path+'/habits/desk-check',json={'completed':True})
        self.a.put(path+'/habits/phone-check',json={'completed':True})
        self.a.put(path+'/habits/desk-check',json={'completed':False})
        current=self.a.get(path).json()
        self.assertEqual(current['habits'],['phone-check'])
        self.assertEqual(current['breaks'],1)

    def test_export_delete_and_retention(self):
        self.a.post(self.base+'/'+self.day+'/breaks',json={'event_id':str(uuid4())})
        export=self.a.get(self.base).json()
        self.assertEqual(export['retention_days'],90)
        self.assertEqual(len(export['daily_activity']),1)
        old=(datetime.now(timezone.utc).date()-timedelta(days=91)).isoformat()
        self.assertEqual(self.a.get(self.base+'/'+old).status_code,422)
        with self.app.state.database.connection() as db:
            db.execute('INSERT INTO daily_activity VALUES (?,?,?,?)',(self.users[0].id,old,'[]',1))
            db.execute('INSERT INTO daily_break_events VALUES (?,?,?)',(self.users[0].id,str(uuid4()),old))
        self.assertEqual(len(self.a.get(self.base).json()['daily_activity']),1)
        ActivityRepository(self.app.state.database).purge(ActivityTracker.today())
        with self.app.state.database.connection() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM daily_activity WHERE day=?',(old,)).fetchone()[0],0)
        self.assertEqual(self.a.delete(self.base).status_code,204)
        self.assertEqual(self.a.get(self.base).json()['daily_activity'],[])
        with self.app.state.database.connection() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM daily_break_events').fetchone()[0],0)

    def test_session_change_and_account_delete(self):
        self.a.post(self.base+'/'+self.day+'/breaks',json={'event_id':str(uuid4())})
        self.assertEqual(self.a.request('DELETE','/api/v1/users/me',json={'password':'a strong private password'}).status_code,204)
        self.assertEqual(self.a.get(self.base).status_code,401)
        with self.app.state.database.connection() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM daily_activity WHERE user_id=?',(self.users[0].id,)).fetchone()[0],0)
            self.assertEqual(db.execute('SELECT count(*) FROM daily_break_events WHERE user_id=?',(self.users[0].id,)).fetchone()[0],0)

    def test_progress_is_private_and_recalculates_after_erasure(self):
        endpoint=self.base+'/progress?day='+self.day+'&days=7'
        with TestClient(self.app) as guest:
            self.assertEqual(guest.get(endpoint).status_code,401)
        self.assertEqual(self.a.get(endpoint,headers={'X-PosturePal-User':self.users[1].id}).status_code,409)
        self.a.post(self.base+'/'+self.day+'/breaks',json={'event_id':str(uuid4())})
        result=self.a.get(endpoint)
        self.assertEqual(result.status_code,200,result.text)
        self.assertEqual(result.json()['totals']['breaks'],1)
        self.assertEqual(self.b.get(endpoint).json()['totals']['breaks'],0)
        self.assertEqual(self.a.get(endpoint.replace('days=7','days=999')).status_code,422)
        self.a.delete(self.base)
        self.assertEqual(self.a.get(endpoint).json()['points'],0)
        self.assertTrue(all(not award['earned'] for award in self.a.get(endpoint).json()['awards']))
