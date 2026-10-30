import unittest
from datetime import date,timedelta
from posturepal.activity.domain.progress import summarize_progress


class ProgressRulesTests(unittest.TestCase):
    def test_empty_progress_is_zero_with_no_awards(self):
        progress=summarize_progress([],date(2026,10,31))
        self.assertEqual(progress['points'],0)
        self.assertEqual(progress['level'],1)
        self.assertTrue(all(not award['earned'] for award in progress['awards']))
        self.assertEqual(len(progress['history']),7)
        self.assertFalse(any(day['active'] for day in progress['history']))

    def test_points_are_capped_and_trophies_use_distinct_active_days(self):
        today=date(2026,10,31)
        rows=[{'day':str(today-timedelta(days=i)),'habits':['first-task','walk-reset','desk-check','phone-check'],'breaks':20} for i in range(7)]
        progress=summarize_progress(rows,today,30)
        self.assertEqual(progress['points'],7*60)
        self.assertEqual(progress['level'],5)
        self.assertEqual(progress['totals']['active_days'],7)
        awards={award['id']:award for award in progress['awards']}
        self.assertTrue(awards['seven-days']['earned'])
        self.assertFalse(awards['thirty-days']['earned'])
        self.assertTrue(awards['ten-breaks']['earned'])
        self.assertEqual(len(progress['history']),30)
        self.assertEqual(sum(day['active'] for day in progress['history']),7)

    def test_undo_or_delete_recalculates_and_future_days_do_not_count(self):
        today=date(2026,10,31)
        data=[{'day':str(today),'habits':[],'breaks':0},{'day':str(today+timedelta(days=1)),'habits':['first-task'],'breaks':99}]
        result=summarize_progress(data,today)
        self.assertEqual(result['points'],0)
        self.assertFalse(any(award['earned'] for award in result['awards']))
