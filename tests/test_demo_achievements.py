import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from datetime import datetime, timezone

from posturepal.activity.domain.progress import summarize_progress
from posturepal.activity.infrastructure.repository import ActivityRepository
from posturepal.commands.seed_achievements import seed_achievements
from posturepal.commands.seed_demo import demo_id, seed_demo
from posturepal.shared.infrastructure.database import Database


class DemoAchievementsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.database = Database.from_path(Path(self.tmp.name) / 'demo.db')
        self.repo = ActivityRepository(self.database)
        self.today = datetime.now(timezone.utc).date()

    def seed_accounts(self):
        seed_demo(self.database, 'isolated demo password 123')

    def test_requires_explicit_demo_accounts(self):
        with self.assertRaises(ValueError):
            seed_achievements(self.database)

    def test_samples_cover_earned_partial_and_empty_progress_without_social_posts(self):
        self.seed_accounts()
        self.assertTrue(seed_achievements(self.database)['seeded'])
        progress = lambda name: summarize_progress(self.repo.export(demo_id(name), self.today), self.today)
        self.assertTrue(all(award['earned'] for award in progress('alex')['awards']))
        maya = progress('maya')
        self.assertEqual(maya['totals']['active_days'], 7)
        self.assertFalse(next(a for a in maya['awards'] if a['id'] == 'ten-breaks')['earned'])
        self.assertEqual(progress('riley')['totals']['breaks'], 0)
        self.assertEqual(progress('jordan')['points'], 0)
        with self.database.connection() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM social_posts').fetchone()[0], 5)
        self.repo.delete(demo_id('alex'))
        self.assertFalse(seed_achievements(self.database)['seeded'])
        self.assertEqual(progress('alex')['points'], 0)

    def test_existing_history_refuses_entire_seed(self):
        self.seed_accounts()
        self.repo.update(demo_id('maya'), self.today, habit='phone-check', completed=True)
        with self.assertRaises(ValueError):
            seed_achievements(self.database)
        self.assertEqual(self.repo.export(demo_id('alex'), self.today), [])
        self.assertEqual(self.repo.read(demo_id('maya'), self.today)['habits'], ['phone-check'])
