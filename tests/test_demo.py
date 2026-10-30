import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from posturepal.shared.infrastructure.database import Database
from posturepal.commands.seed_demo import seed_demo
from posturepal.users.infrastructure.repository import UserRepository
from posturepal.users.application.accounts import verify_password


class DemoTests(unittest.TestCase):
    def test_demo_is_explicit_and_idempotent(self):
        with TemporaryDirectory() as directory:
            database=Database.from_path(Path(directory)/'demo.db')
            with self.assertRaises(ValueError):
                seed_demo(database,'')
            password='unique demo password 123'
            self.assertTrue(seed_demo(database,password)['seeded'])
            users=UserRepository(database)
            before=users.credentials('alex@demo.posturepal.test')['password_hash']
            self.assertTrue(verify_password(password,before))
            self.assertFalse(seed_demo(database,'another unique password')['seeded'])
            self.assertEqual(users.credentials('alex@demo.posturepal.test')['password_hash'],before)
            self.assertEqual(users.list('demo',25,0)['total'],4)
            self.assertNotEqual(users.credentials('maya@demo.posturepal.test')['password_hash'],before)
            with database.connection() as db:
                self.assertEqual(db.execute('SELECT count(*) FROM exercises').fetchone()[0],8)
                self.assertEqual(db.execute('SELECT count(*) FROM social_posts').fetchone()[0],5)
            database.engine.dispose()
