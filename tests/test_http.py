import unittest
from tempfile import TemporaryDirectory
from pathlib import Path

from fastapi.testclient import TestClient

from posturepal.server import VERSION, create_app


class HttpTests(unittest.TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / 'catalog.db'
        self.token = 'test-admin-token-' + 'a' * 48
        self.client = TestClient(create_app(self.path, self.token))
        self.addCleanup(self.client.close)

    def test_health_reports_release_version(self):
        response = self.client.get('/api/v1/health')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'status': 'ok', 'version': VERSION})

    def test_search_combines_filters_and_serializes_steps(self):
        response = self.client.get('/api/v1/exercises', params={'q': 'ROLL', 'area': 'shoulders'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual([e['id'] for e in response.json()], ['shoulder-rolls'])
        self.assertIsInstance(response.json()[0]['steps'], list)

    def test_detail_and_missing_exercise(self):
        self.assertEqual(self.client.get('/api/v1/exercises/neck-release').json()['id'], 'neck-release')
        response = self.client.get('/api/v1/exercises/missing')
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {'detail': 'Exercise not found'})

    def test_unknown_api_does_not_fall_through_to_frontend(self):
        response = self.client.get('/api/v1/missing')
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {'detail': 'Route not found'})

    def test_frontend_and_vendored_vue_are_served(self):
        for path, content in [('/', 'PosturePal'), ('/src/main.js', 'createApp'),
                              ('/vendor/vue.esm-browser.prod.js', 'vue v3.5.13')]:
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                self.assertIn(content, response.text)

    def test_openapi_documents_exercises_and_version(self):
        schema = self.client.get('/openapi.json').json()
        self.assertEqual(schema['info']['version'], VERSION)
        self.assertIn('/api/v1/exercises/{exercise_id}', schema['paths'])
        self.assertEqual(self.client.get('/docs').status_code, 200)


    def payload(self):
        return {'id': 'test-movement', 'name': 'Test movement', 'area': 'Back',
                'duration': 60, 'description': 'A gentle movement.', 'steps': ['Move gently.'],
                'position': 'Seated', 'symbol': 'twist'}

    @property
    def auth(self):
        return {'Authorization': f'Bearer {self.token}'}

    def test_all_mutations_require_admin(self):
        for method, path, data in [('post', '/api/v1/exercises', self.payload()),
                                   ('put', '/api/v1/exercises/neck-release', {k:v for k,v in self.payload().items() if k != 'id'}),
                                   ('delete', '/api/v1/exercises/neck-release', None)]:
            for headers in [{}, {'Authorization': 'Bearer wrong'}]:
                with self.subTest(method=method, headers=headers):
                    kwargs = {'headers': headers}
                    if data is not None:
                        kwargs['json'] = data
                    self.assertEqual(getattr(self.client, method)(path, **kwargs).status_code, 401)
        self.assertEqual(len(self.client.get('/api/v1/exercises').json()), 8)

    def test_crud_is_durable_and_conflicts_are_reported(self):
        payload = self.payload()
        response = self.client.post('/api/v1/exercises', headers=self.auth, json=payload)
        self.assertEqual(response.status_code, 201, response.text)
        self.assertEqual(self.client.post('/api/v1/exercises', headers=self.auth, json=payload).status_code, 409)
        update = {k:v for k,v in payload.items() if k != 'id'}
        update['name'] = 'Updated movement'
        self.assertEqual(self.client.put('/api/v1/exercises/test-movement', headers=self.auth, json=update).status_code, 200)
        with TestClient(create_app(self.path, self.token)) as restarted:
            self.assertEqual(restarted.get('/api/v1/exercises/test-movement').json()['name'], 'Updated movement')
        self.assertEqual(self.client.delete('/api/v1/exercises/test-movement', headers=self.auth).status_code, 204)
        self.assertEqual(self.client.get('/api/v1/exercises/test-movement').status_code, 404)
        self.assertEqual(self.client.delete('/api/v1/exercises/test-movement', headers=self.auth).status_code, 404)
        self.assertEqual(self.client.put('/api/v1/exercises/missing', headers=self.auth, json=update).status_code, 404)

    def test_invalid_fields_are_rejected(self):
        for change in [{'duration': 0}, {'duration': '60'}, {'id': '../escape'},
                       {'name': '   '}, {'steps': []}, {'steps': [' ']},
                       {'area': 'invalid'}, {'symbol': '<script>'}, {'unexpected': True}]:
            with self.subTest(change=change):
                self.assertEqual(self.client.post('/api/v1/exercises', headers=self.auth,
                    json={**self.payload(), **change}).status_code, 422)

    def test_empty_library_is_not_reseeded_after_restart(self):
        for item in self.client.get('/api/v1/exercises').json():
            self.client.delete('/api/v1/exercises/' + item['id'], headers=self.auth)
        with TestClient(create_app(self.path, self.token)) as restarted:
            self.assertEqual(restarted.get('/api/v1/exercises').json(), [])

    def test_unconfigured_admin_fails_closed(self):
        with TestClient(create_app(self.path, '')) as unconfigured:
            self.assertEqual(unconfigured.post('/api/v1/exercises', headers=self.auth, json=self.payload()).status_code, 503)
            self.assertEqual(unconfigured.get('/api/v1/exercises').status_code, 200)

    def test_admin_session_and_security_headers(self):
        self.assertEqual(self.client.get('/api/v1/admin/session').status_code, 401)
        response = self.client.get('/api/v1/admin/session', headers=self.auth)
        self.assertEqual(response.json(), {'role': 'admin'})
        self.assertEqual(response.headers['cache-control'], 'no-store')
        self.assertEqual(response.headers['x-frame-options'], 'DENY')
        self.assertEqual(self.client.get('/admin.html').status_code, 200)

    def test_dashboard_is_protected_and_tracks_catalog_changes(self):
        self.assertEqual(self.client.get('/api/v1/admin/dashboard').status_code, 401)
        self.assertEqual(self.client.get('/api/v1/admin/dashboard', headers={'Authorization': 'Bearer wrong'}).status_code, 401)
        response = self.client.get('/api/v1/admin/dashboard', headers=self.auth)
        self.assertEqual(response.status_code, 200)
        stats = response.json()
        items = self.client.get('/api/v1/exercises').json()
        self.assertEqual(stats['total_exercises'], len(items))
        self.assertEqual(stats['total_duration_seconds'], sum(item['duration'] for item in items))
        self.assertEqual(stats['quick_breaks'], sum(item['duration'] <= 60 for item in items))
        self.assertEqual(sum(item['count'] for item in stats['body_areas']), len(items))
        self.assertEqual(sum(item['count'] for item in stats['positions']), len(items))
        self.client.post('/api/v1/exercises', json=self.payload(), headers=self.auth)
        updated = self.client.get('/api/v1/admin/dashboard', headers=self.auth).json()
        self.assertEqual(updated['total_exercises'], stats['total_exercises'] + 1)
        self.assertEqual(updated['total_duration_seconds'], stats['total_duration_seconds'] + 60)
        for item in self.client.get('/api/v1/exercises').json():
            self.client.delete('/api/v1/exercises/' + item['id'], headers=self.auth)
        empty = self.client.get('/api/v1/admin/dashboard', headers=self.auth).json()
        self.assertEqual(empty['total_exercises'], 0)
        self.assertEqual(empty['average_duration_seconds'], 0)
        self.assertTrue(all(item['count'] == 0 for item in empty['body_areas']))

    def test_break_coaching_endpoints_and_page(self):
        response = self.client.get('/api/v1/breaks')
        self.assertEqual(response.status_code, 200)
        routines = response.json()
        self.assertEqual({item['id'] for item in routines}, {'standard', 'pain-relief', 'strength', 'movement-habit'})
        for routine in routines:
            self.assertGreater(routine['duration'], 0)
            self.assertGreaterEqual(len(routine['steps']), 3)
            self.assertTrue(routine['caution'])
        checks = self.client.get('/api/v1/posture-checks').json()
        self.assertEqual({item['id'] for item in checks}, {'desk', 'phone'})
        self.assertTrue(all(len(item['items']) >= 3 for item in checks))
        habits = self.client.get('/api/v1/daily-habits').json()
        self.assertEqual(len({item['id'] for item in habits}), 4)
        self.assertTrue(all(item['name'] and item['cue'] for item in habits))
        for path in ['/breaks.html', '/src/breaks.js', '/src/breaks.css', '/src/composables/useDailyHabits.js']:
            self.assertEqual(self.client.get(path).status_code, 200)


    def test_default_start_page_is_dashboard_and_library_remains_accessible(self):
        home = self.client.get('/')
        self.assertEqual(home.status_code, 200)
        self.assertIn('PosturePal · Dashboard', home.text)
        self.assertIn('/src/dashboard.js', home.text)
        self.assertNotIn('/src/main.js', home.text)
        library = self.client.get('/library.html')
        self.assertEqual(library.status_code, 200)
        self.assertIn('/src/main.js', library.text)
        for path in ['/src/dashboard.js', '/src/dashboard.css']:
            self.assertEqual(self.client.get(path).status_code, 200)
