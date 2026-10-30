"""Achievements derived from retained self-reported activity, never separate health records."""
from datetime import timedelta


def summarize_progress(records, today, days=7):
    retained={row['day']:row for row in records if row['day']<=today.isoformat()}
    active=lambda row: bool(row['breaks'] or row['habits'])
    totals={
        'breaks':sum(row['breaks'] for row in retained.values()),
        'habit_checks':sum(len(row['habits']) for row in retained.values()),
        'active_days':sum(active(row) for row in retained.values()),
        'complete_days':sum(len(row['habits'])==4 for row in retained.values()),
    }
    points=sum((10 if active(row) else 0)+5*len(row['habits'])+10*min(row['breaks'],3) for row in retained.values())
    history=[]
    for offset in reversed(range(days)):
        day=(today-timedelta(days=offset)).isoformat()
        row=retained.get(day,{'day':day,'habits':[],'breaks':0})
        history.append({'day':day,'breaks':row['breaks'],'habits':len(row['habits']),'active':active(row)})
    definitions=[
        ('first-break','First reset','badge','Complete one timed break.',totals['breaks'],1,'✦'),
        ('first-habit','A small step','badge','Check off one daily habit.',totals['habit_checks'],1,'🌱'),
        ('balanced-day','Daily balance','badge','Check all four habits in a day.',totals['complete_days'],1,'◈'),
        ('ten-breaks','Room to reset','trophy','Complete ten breaks across your recorded days.',totals['breaks'],10,'🏆'),
        ('seven-days','Showing up','trophy','Record activity on seven different days.',totals['active_days'],7,'🏅'),
        ('thirty-days','Everyday momentum','trophy','Record activity on thirty different days.',totals['active_days'],30,'🏆'),
    ]
    awards=[{'id':id,'name':name,'type':kind,'description':description,'value':value,'target':target,
             'progress':min(value,target),'earned':value>=target,'symbol':symbol}
            for id,name,kind,description,value,target,symbol in definitions]
    current=retained.get(today.isoformat(),{'habits':[],'breaks':0})
    message=('You made space for yourself today. Rest counts too.' if current['breaks'] and len(current['habits'])==4
             else 'One small action is enough to start. Choose what feels comfortable.' if not active(current)
             else 'A little progress counts. Keep a rhythm that works for you.')
    return {'window_days':90,'range_days':days,'totals':totals,'points':points,'level':points//100+1,
            'level_progress':points%100,'next_level_points':100,'awards':awards,'history':history,'motivation':message}
