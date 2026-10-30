import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from fastapi.testclient import TestClient
from posturepal.server import create_app
from posturepal.users.infrastructure.repository import UserRepository
from posturepal.users.application.accounts import Accounts


class SocialTests(unittest.TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/'social.db'
        self.app=create_app(self.path,'admin-token-'+'x'*48)
        accounts=Accounts(UserRepository(self.path))
        self.clients=[]
        self.ids=[]
        for name in ['alice','bob','carol']:
            user=accounts.create(name+'@example.com',name,'a strong password')
            self.ids.append(user.id)
            client=TestClient(self.app)
            client.headers['X-PosturePal-Request']='1'
            client.post('/api/v1/auth/login',json={'email':user.email,'password':'a strong password'})
            self.clients.append(client)
            self.addCleanup(client.close)
        self.a,self.b,self.c=self.clients
        self.alice,self.bob,self.carol=self.ids

    def connect(self):
        self.assertEqual(self.a.post('/api/v1/social/friends/'+self.bob).status_code,204)
        self.assertEqual(self.b.put('/api/v1/social/friends/'+self.alice).status_code,204)

    def publish(self,audience='friends'):
        response=self.a.post('/api/v1/social/activities',json={'kind':'break','text':'Took a gentle break','audience':audience})
        self.assertEqual(response.status_code,201,response.text)
        return '/api/v1/social/activities/'+response.json()['id']

    def privacy(self,**changes):
        settings=self.a.get('/api/v1/social').json()['privacy']
        return self.a.put('/api/v1/social/privacy',json={**settings,**changes})

    def test_requests_must_be_accepted_by_recipient(self):
        self.assertEqual(self.a.post('/api/v1/social/friends/'+self.bob).status_code,204)
        self.assertEqual(self.a.put('/api/v1/social/friends/'+self.bob).status_code,404)
        self.assertEqual(self.c.put('/api/v1/social/friends/'+self.alice).status_code,404)
        self.assertEqual(self.b.put('/api/v1/social/friends/'+self.alice).status_code,204)
        response=self.a.get('/api/v1/social').json()
        self.assertEqual(response['statistics']['friends'],1)
        self.assertNotIn('email',str(response['friends']))

    def test_private_and_friend_post_access_is_enforced_everywhere(self):
        self.connect()
        private=self.publish('private')
        shared=self.publish()
        self.assertEqual(self.a.get(private).status_code,200)
        self.assertEqual(self.b.get(private).status_code,404)
        self.assertEqual(self.b.put(private+'/like').status_code,404)
        self.assertEqual(self.c.get(shared).status_code,404)
        self.assertEqual(self.b.get(shared).status_code,200)
        self.assertEqual(len(self.b.get('/api/v1/social').json()['feed']['items']),1)
        self.assertEqual(self.b.delete(shared).status_code,404)
        self.assertEqual(self.b.put(shared,json={'audience':'private'}).status_code,404)
        self.assertEqual(self.a.put(shared,json={'audience':'private'}).status_code,204)
        self.assertEqual(self.b.get(shared).status_code,404)

    def test_engagement_statistics_and_comment_moderation(self):
        self.connect()
        path=self.publish()
        for _ in range(2):self.b.put(path+'/like')
        self.b.post(path+'/comments',json={'text':'Well done!'})
        post=self.b.get(path).json()
        self.assertEqual(post['likes'],1)
        self.assertEqual(len(post['comments']),1)
        stats=self.a.get('/api/v1/social/statistics').json()
        self.assertEqual(stats['likes_received'],1)
        self.assertEqual(stats['comments_received'],1)
        cid=post['comments'][0]['id']
        self.assertEqual(self.c.delete(path+'/comments/'+cid).status_code,404)
        self.assertEqual(self.a.delete(path+'/comments/'+cid).status_code,204)
        self.b.delete(path+'/like')
        self.assertEqual(self.a.get('/api/v1/social/statistics').json()['likes_received'],0)
        self.privacy(allow_comments=False)
        self.assertEqual(self.b.post(path+'/comments',json={'text':'Another'}).status_code,409)

    def test_privacy_unfriend_and_block_revoke_access(self):
        self.connect()
        path=self.publish()
        self.privacy(sharing_enabled=False)
        self.assertEqual(self.b.get(path).status_code,404)
        self.assertEqual(self.b.get('/api/v1/social').json()['feed']['items'],[])
        self.privacy(sharing_enabled=True)
        self.assertEqual(self.b.get(path).status_code,200)
        self.a.delete('/api/v1/social/friends/'+self.bob)
        self.assertEqual(self.b.get(path).status_code,404)
        self.connect()
        self.a.put('/api/v1/social/blocks/'+self.bob)
        self.assertEqual(self.b.get(path).status_code,404)
        self.assertEqual(self.b.post('/api/v1/social/friends/'+self.alice).status_code,404)
        self.a.delete('/api/v1/social/blocks/'+self.bob)
        self.assertEqual(self.b.get(path).status_code,404)

    def test_defaults_authentication_and_validation(self):
        with TestClient(self.app) as guest:
            self.assertEqual(guest.get('/api/v1/social').status_code,401)
            self.assertEqual(guest.get('/api/v1/social/statistics').status_code,401)
        settings=self.a.get('/api/v1/social').json()['privacy']
        self.assertEqual(settings['default_audience'],'private')
        self.assertEqual(self.a.post('/api/v1/social/friends/'+self.alice).status_code,409)
        self.privacy(accept_requests=False)
        self.assertEqual(self.b.post('/api/v1/social/friends/'+self.alice).status_code,404)
        self.assertEqual(self.a.post('/api/v1/social/activities',json={'kind':'break','text':'  '}).status_code,422)
        self.assertEqual(self.a.post('/api/v1/social/activities',json={'kind':'break','text':'hi','audience':'public'}).status_code,422)
        path=self.publish('private')
        self.assertEqual(self.a.delete(path).status_code,204)
        self.assertEqual(self.a.get(path).status_code,404)
        self.assertEqual(self.a.get('/social.html').status_code,200)
