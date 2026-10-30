"""Explicit synthetic achievement history for existing demo accounts only."""
import json
from datetime import datetime, timedelta, timezone

from posturepal.activity.domain.rules import HABIT_IDS
from posturepal.commands.seed_demo import demo_id
from posturepal.shared.infrastructure.database import Database

MARKER = 'demo-achievements-v1'
SAMPLES = (('alex', 30), ('maya', 7), ('riley', 1))


def seed_achievements(database):
    today = datetime.now(timezone.utc).date()
    with database.connection() as db:
        db.lock()
        if db.execute('SELECT 1 FROM metadata WHERE `key`=?', (MARKER,)).fetchone():
            return {'seeded': False, 'message': 'Achievement samples already seeded; no history changed'}
        if not db.execute("SELECT 1 FROM metadata WHERE `key`='demo-v1'").fetchone():
            raise ValueError('Run seed_demo first in your development/demo database')
        for name, _ in SAMPLES:
            uid = demo_id(name)
            user = db.execute('SELECT email FROM users WHERE id=?', (uid,)).fetchone()
            if not user or user['email'] != name + '@demo.posturepal.test':
                raise ValueError('Expected demo account missing or changed; refusing to seed')
            for table in ('daily_activity', 'daily_break_events'):
                if db.execute(f'SELECT 1 FROM {table} WHERE user_id=?', (uid,)).fetchone():
                    raise ValueError('Demo account already has activity; refusing to overwrite or mix history')
        for name, days in SAMPLES:
            for offset in range(days):
                habits = sorted(HABIT_IDS) if name == 'alex' else ['desk-check']
                breaks = 2 if name == 'alex' else (1 if name == 'maya' else 0)
                db.execute('INSERT INTO daily_activity (user_id,day,habits,breaks) VALUES (?,?,?,?)',
                           (demo_id(name), str(today - timedelta(days=offset)), json.dumps(habits), breaks))
        db.execute('INSERT INTO metadata (`key`) VALUES (?)', (MARKER,))
    return {'seeded': True, 'users': 3, 'days': 38,
            'message': 'Synthetic achievement history created for demo accounts only; sign in to view it'}


def main():
    try:
        result = seed_achievements(Database.configured())
    except ValueError as error:
        raise SystemExit(str(error)) from None
    print(json.dumps(result))


if __name__ == '__main__':
    main()
