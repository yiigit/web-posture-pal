from datetime import datetime, timezone
from posturepal.activity.domain.rules import HABIT_IDS, RETENTION_DAYS, validate_day


class ActivityTracker:
    def __init__(self,repository):
        self.repository=repository

    @staticmethod
    def today():
        return datetime.now(timezone.utc).date()

    def read(self,uid,day):
        validate_day(day,self.today())
        return self.repository.read(uid,day)

    def habit(self,uid,day,habit,completed):
        validate_day(day,self.today(),write=True)
        if habit not in HABIT_IDS:
            raise ValueError('Unknown daily habit')
        return self.repository.update(uid,day,habit=habit,completed=completed)

    def record_break(self,uid,day,event_id):
        validate_day(day,self.today(),write=True)
        return self.repository.update(uid,day,event_id=event_id)

    def export(self,uid):
        return {'retention_days':RETENTION_DAYS,'daily_activity':self.repository.export(uid,self.today())}

    def delete(self,uid):
        self.repository.delete(uid)
