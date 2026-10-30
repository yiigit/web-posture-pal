import sqlite3
from contextlib import closing
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi.testclient import TestClient
from posturepal.server import create_app


class UserTests(unittest.TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / 'accounts.db'
        self.token = 'bootstrap-admin-' + 'a' * 48
        self.client = TestClient(create_app(self.path, self.token))
        self.client.headers['X-PosturePal-Request'] = '1'
        self.addCleanup(self.client.close)
        self.admin = {'Authorization': 'Bearer ' + self.token}
        self.payload = {'email': 'member@example.com', 'display_name': 'Member', 'password': 'a long secret password'}

    def register_login(self):
        response = self.client.post('/api/v1/auth/register', json=self.payload)
        self.assertEqual(response.status_code, 201, response.text)
        login = self.client.post('/api/v1/auth/login', json={k:self.payload[k] for k in ['email','password']})
        self.assertEqual(login.status_code, 200, login.text)
        return login.json()

    def test_register_profile_logout_and_password_storage(self):
        user = self.register_login()
        self.assertEqual(user['role'], 'member')
        self.assertNotIn('password_hash', user)
        with closing(sqlite3.connect(self.path)) as db:
            stored = db.execute('SELECT password_hash FROM users').fetchone()[0]
            self.assertTrue(stored.startswith('scrypt$'))
            self.assertNotIn(self.payload['password'], stored)
            digest = db.execute('SELECT digest FROM user_sessions').fetchone()[0]
            self.assertNotEqual(digest, self.client.cookies['posturepal_session'])
        profile = {'display_name':'New Name','bio':'My profile','timezone':'Europe/Brussels','theme':'dark'}
        self.assertEqual(self.client.put('/api/v1/users/me', json=profile).json()['display_name'], 'New Name')
        with TestClient(create_app(self.path, self.token)) as restarted:
            restarted.cookies.update(self.client.cookies)
            self.assertEqual(restarted.get('/api/v1/users/me').json()['bio'], 'My profile')
        self.assertEqual(self.client.post('/api/v1/auth/logout').status_code, 204)
        self.assertEqual(self.client.get('/api/v1/users/me').status_code, 401)

    def test_member_cannot_manage_users_or_inject_roles(self):
        self.register_login()
        self.assertEqual(self.client.get('/api/v1/admin/users').status_code, 403)
        self.assertEqual(self.client.get('/api/v1/admin/dashboard').status_code, 403)
        self.assertEqual(self.client.put('/api/v1/users/me', json={'display_name':'x','role':'admin'}).status_code, 422)
        self.assertEqual(self.client.post('/api/v1/auth/register', json={**self.payload,'email':'other@example.com','role':'admin'}).status_code, 422)
        self.assertEqual(self.client.get('/api/v1/users/me').json()['role'], 'member')

    def test_password_change_revokes_sessions_and_rejects_wrong_password(self):
        self.register_login()
        self.assertEqual(self.client.put('/api/v1/users/me/password', json={'current_password':'wrong','new_password':'a new long password'}).status_code, 401)
        self.assertEqual(self.client.put('/api/v1/users/me/password', json={'current_password':self.payload['password'],'new_password':'a new long password'}).status_code, 204)
        self.assertEqual(self.client.get('/api/v1/users/me').status_code, 401)
        self.assertEqual(self.client.post('/api/v1/auth/login', json={'email':self.payload['email'],'password':self.payload['password']}).status_code, 401)
        self.assertEqual(self.client.post('/api/v1/auth/login', json={'email':self.payload['email'],'password':'a new long password'}).status_code, 200)

    def test_admin_management_and_last_admin_protection(self):
        user = self.register_login()
        path = '/api/v1/admin/users/' + user['id']
        promoted = self.client.put(path+'/access', headers=self.admin, json={'role':'admin','active':True})
        self.assertEqual(promoted.status_code, 200)
        self.assertEqual(self.client.get('/api/v1/users/me').status_code, 401)
        self.client.post('/api/v1/auth/login', json={'email':self.payload['email'],'password':self.payload['password']})
        self.assertEqual(self.client.get('/api/v1/admin/dashboard').status_code, 200)
        self.assertEqual(self.client.put(path+'/access', headers=self.admin,json={'role':'member','active':True}).status_code, 409)
        self.assertEqual(self.client.delete(path, headers=self.admin).status_code, 409)
        other = self.client.post('/api/v1/admin/users', headers=self.admin,json={**self.payload,'email':'admin@example.com','role':'admin'}).json()
        self.assertIn('id', other)
        listed = self.client.get('/api/v1/admin/users?q=admin', headers=self.admin).json()
        self.assertEqual(listed['total'], 1)
        self.assertNotIn('password_hash', listed['items'][0])
        self.assertEqual(self.client.put(path+'/access', headers=self.admin,json={'role':'member','active':False}).status_code, 200)
        self.assertEqual(self.client.post('/api/v1/auth/login', json={'email':self.payload['email'],'password':self.payload['password']}).status_code, 401)
        self.assertEqual(self.client.delete(path, headers=self.admin).status_code, 204)

    def test_csrf_and_cookie_attributes(self):
        response = self.client.post('/api/v1/auth/login', headers={'X-PosturePal-Request':''}, json={'email':self.payload['email'],'password':self.payload['password']})
        self.assertEqual(response.status_code, 403)
        self.register_login()
        response = self.client.post('/api/v1/auth/login',json={'email':self.payload['email'],'password':self.payload['password']})
        self.assertIn('HttpOnly', response.headers['set-cookie'])
        self.assertIn('SameSite=strict', response.headers['set-cookie'])
        self.assertEqual(self.client.post('/api/v1/auth/logout',headers={'X-PosturePal-Request':''}).status_code, 403)

    def test_duplicate_validation_and_login_throttle(self):
        self.register_login()
        self.assertEqual(self.client.post('/api/v1/auth/register',json={**self.payload,'email':'MEMBER@example.com'}).status_code, 409)
        self.assertEqual(self.client.post('/api/v1/auth/register',json={**self.payload,'password':'short'}).status_code, 422)
        for _ in range(9):
            self.client.post('/api/v1/auth/login',json={'email':'missing@example.com','password':'wrong long password'})
        self.assertEqual(self.client.post('/api/v1/auth/login',json={'email':'missing@example.com','password':'wrong long password'}).status_code, 429)

    def test_admin_reset_and_self_delete(self):
        user = self.register_login()
        self.assertEqual(self.client.put('/api/v1/admin/users/'+user['id']+'/password',headers=self.admin,json={'new_password':'reset long password'}).status_code, 204)
        self.assertEqual(self.client.get('/api/v1/users/me').status_code, 401)
        self.client.post('/api/v1/auth/login',json={'email':self.payload['email'],'password':'reset long password'})
        self.assertEqual(self.client.request('DELETE','/api/v1/users/me',json={'password':'reset long password'}).status_code, 204)
        self.assertEqual(self.client.get('/api/v1/users/me').status_code, 401)
        for path in ['/account.html','/users.html','/src/account.js','/src/users.js']:
            self.assertEqual(self.client.get(path).status_code, 200)

    def test_expired_sessions_and_invalid_profiles(self):
        self.register_login()
        self.assertEqual(self.client.put('/api/v1/users/me',json={'display_name':'Name','timezone':'Invalid/Zone'}).status_code, 422)
        with closing(sqlite3.connect(self.path)) as db:
            db.execute('UPDATE user_sessions SET expires_at=0')
            db.commit()
        self.assertEqual(self.client.get('/api/v1/users/me').status_code, 401)
