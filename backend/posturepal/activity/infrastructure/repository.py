import json
from datetime import timedelta
from posturepal.activity.domain.rules import RETENTION_DAYS


class ActivityRepository:
    def __init__(self,database):
        self.connection=database.connection

    @staticmethod
    def empty(day):
        return {'day':str(day),'habits':[],'breaks':0}

    def read(self,uid,day):
        with self.connection() as db:
            row=db.execute('SELECT * FROM daily_activity WHERE user_id=? AND day=?',(uid,str(day))).fetchone()
        return {'day':row['day'],'habits':json.loads(row['habits']),'breaks':row['breaks']} if row else self.empty(day)

    def update(self,uid,day,habit=None,completed=False,event_id=None):
        with self.connection() as db:
            db.lock()
            db.insert_once('daily_activity',{'user_id':uid,'day':str(day),'habits':'[]','breaks':0})
            row=db.execute('SELECT * FROM daily_activity WHERE user_id=? AND day=?',(uid,str(day))).fetchone()
            habits=set(json.loads(row['habits']))
            count=row['breaks']
            if habit:
                habits.add(habit) if completed else habits.discard(habit)
            if event_id:
                if not db.execute('SELECT 1 FROM daily_break_events WHERE user_id=? AND event_id=?',(uid,event_id)).fetchone():
                    if count>=1000:
                        raise ValueError('Daily break limit reached')
                    db.execute('INSERT INTO daily_break_events VALUES (?,?,?)',(uid,event_id,str(day)))
                    count+=1
            db.execute('UPDATE daily_activity SET habits=?,breaks=? WHERE user_id=? AND day=?',(json.dumps(sorted(habits)),count,uid,str(day)))
            return {'day':str(day),'habits':sorted(habits),'breaks':count}

    def export(self,uid,today):
        cutoff=str(today-timedelta(days=RETENTION_DAYS-1))
        with self.connection() as db:
            rows=db.execute('SELECT * FROM daily_activity WHERE user_id=? AND day>=? ORDER BY day',(uid,cutoff)).fetchall()
        return [{'day':row['day'],'habits':json.loads(row['habits']),'breaks':row['breaks']} for row in rows]

    def delete(self,uid):
        with self.connection() as db:
            db.lock()
            db.execute('DELETE FROM daily_break_events WHERE user_id=?',(uid,))
            db.execute('DELETE FROM daily_activity WHERE user_id=?',(uid,))

    def purge(self,today):
        cutoff=str(today-timedelta(days=RETENTION_DAYS-1))
        with self.connection() as db:
            db.lock()
            db.execute('DELETE FROM daily_break_events WHERE day<?',(cutoff,))
            return db.execute('DELETE FROM daily_activity WHERE day<?',(cutoff,)).rowcount
