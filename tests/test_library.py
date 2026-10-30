import unittest
from posturepal.movement.application.library import MovementLibrary
from posturepal.movement.infrastructure.catalog import CatalogRepository

class LibraryTests(unittest.TestCase):
    def setUp(self):
        self.library = MovementLibrary(CatalogRepository())

    def test_catalog_has_unique_ids_and_actionable_steps(self):
        items = self.library.search()
        self.assertEqual(len(items), 8)
        self.assertEqual(len({item.id for item in items}), len(items))
        for item in items:
            self.assertGreater(item.duration, 0)
            self.assertGreaterEqual(len(item.steps), 3)

    def test_search_combines_body_area_and_case_insensitive_query(self):
        results = self.library.search('ROLL', 'shoulders')
        self.assertEqual([item.id for item in results], ['shoulder-rolls'])
        self.assertEqual(self.library.search('roll', 'Back'), [])

    def test_unknown_exercise_returns_none(self):
        self.assertIsNone(self.library.get('missing'))

if __name__ == '__main__':
    unittest.main()
