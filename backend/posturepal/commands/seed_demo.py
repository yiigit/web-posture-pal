"""Explicit, transactional demo fixture. Never runs during normal startup."""
import os
import time
from uuid import NAMESPACE_URL, uuid5

from posturepal.shared.infrastructure.database import Database
from posturepal.movement.infrastructure.repository import ExerciseRepository
from posturepal.users.application.accounts import hash_password


def demo_id(name):
    return str(uuid5(NAMESPACE_URL, 'https://posturepal.example/demo/' + name))


def seed_demo(database, password):
    if not 12 <= len(password) <= 128:
        raise ValueError('Set POSTUREPAL_DEMO_PASSWORD to a unique 12–128 character password')
    ExerciseRepository(database)
    now = int(time.time())
    people = [('alex','Alex Morgan','admin','sportive'),('maya','Maya Chen','member','light'),
              ('riley','Riley James','member','dark'),('jordan','Jordan Lee','member','nike')]
    with database.connection() as db:
        db.lock()
        if db.execute("SELECT 1 FROM metadata WHERE `key`='demo-v1'").fetchone():
            return {'seeded':False,'message':'Demo data already exists; no accounts or passwords changed'}
        for name,display,role,theme in people:
            email = name + '@demo.posturepal.test'
            existing = db.execute('SELECT id FROM users WHERE email=? OR id=?',(email,demo_id(name))).fetchone()
            if existing:
                raise ValueError('Demo account identifiers already exist; refusing to overwrite user data')
            db.execute('INSERT INTO users VALUES (?,?,?,?,?,?,?,?,?,?)',
                       (demo_id(name),email,display,'Demo profile · building small movement habits.','Europe/Brussels',theme,role,1,now,hash_password(password)))
            db.execute('INSERT INTO social_settings VALUES (?,?,?,?,?)',(demo_id(name),1,1,'private',1))
        alex = demo_id('alex')
        for name in ['maya','riley']:
            db.execute('INSERT INTO friendships VALUES (?,?,?,?)',(alex,demo_id(name),'accepted',now))
        db.execute('INSERT INTO friendships VALUES (?,?,?,?)',(demo_id('jordan'),alex,'pending',now))
        activities=[('alex','break','Demo: took a comfortable movement break between tasks.','friends'),
                    ('maya','habit','Demo: checked my desk setup before starting the day.','friends'),
                    ('riley','movement','Demo: found a gentle movement that fits my workspace.','friends'),
                    ('alex','update','Demo: a private reminder to change position regularly.','private'),
                    ('maya','break','Demo: stepped away from the screen for a short reset.','friends')]
        for index,(name,kind,content,audience) in enumerate(activities):
            db.execute('INSERT INTO social_posts VALUES (?,?,?,?,?,?)',(demo_id('post-'+str(index)),demo_id(name),kind,content,audience,now-index*3600))
        db.execute('INSERT INTO social_likes VALUES (?,?)',(demo_id('post-0'),demo_id('maya')))
        db.execute('INSERT INTO social_likes VALUES (?,?)',(demo_id('post-0'),demo_id('riley')))
        db.execute('INSERT INTO social_comments VALUES (?,?,?,?,?)',(demo_id('comment-0'),demo_id('post-0'),demo_id('maya'),'Demo: small steps count. Nicely done!',now))
        db.execute("INSERT INTO metadata (`key`) VALUES ('demo-v1')")
    return {'seeded':True,'users':4,'activities':5,'message':'Demo data created; sign in as alex@demo.posturepal.test with your supplied demo password'}


def main():
    import json
    try:
        result=seed_demo(Database.configured(),os.getenv('POSTUREPAL_DEMO_PASSWORD',''))
    except ValueError as error:
        raise SystemExit(str(error)) from None
    print(json.dumps(result))


if __name__=='__main__':
    main()
