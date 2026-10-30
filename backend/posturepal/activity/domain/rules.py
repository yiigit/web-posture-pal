from datetime import date, timedelta

RETENTION_DAYS = 90
HABIT_IDS = frozenset({'first-task', 'walk-reset', 'desk-check', 'phone-check'})


def validate_day(day: date, today: date, write=False):
    if day < today - timedelta(days=RETENTION_DAYS - 1) or day > today + timedelta(days=1):
        raise ValueError('Activity date is outside the retention window')
    # Allow browser-local calendar dates on either side of UTC midnight.
    if write and day < today - timedelta(days=1):
        raise ValueError('Only current daily activity can be recorded')
