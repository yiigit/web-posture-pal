import time
from uuid import uuid4
from posturepal.social.domain.policy import can_view


class SocialRepository:
    def __init__(self, users):
        self.connection = users.connection
        with self.connection() as db:
            db.executescript('''
            CREATE TABLE IF NOT EXISTS social_settings (
                user_id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
                accept_requests INTEGER NOT NULL DEFAULT 1,
                sharing_enabled INTEGER NOT NULL DEFAULT 1,
                default_audience TEXT NOT NULL DEFAULT 'private',
                allow_comments INTEGER NOT NULL DEFAULT 1);
            CREATE TABLE IF NOT EXISTS friendships (
                sender TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                recipient TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                status TEXT NOT NULL, created_at INTEGER NOT NULL,
                PRIMARY KEY(sender,recipient));
            CREATE TABLE IF NOT EXISTS social_blocks (
                blocker TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                blocked TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                PRIMARY KEY(blocker,blocked));
            CREATE TABLE IF NOT EXISTS social_posts (
                id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                kind TEXT NOT NULL, text TEXT NOT NULL, audience TEXT NOT NULL, created_at INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS social_likes (
                post_id TEXT NOT NULL REFERENCES social_posts(id) ON DELETE CASCADE,
                user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                PRIMARY KEY(post_id,user_id));
            CREATE TABLE IF NOT EXISTS social_comments (
                id TEXT PRIMARY KEY, post_id TEXT NOT NULL REFERENCES social_posts(id) ON DELETE CASCADE,
                user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE, text TEXT NOT NULL, created_at INTEGER NOT NULL);
            CREATE INDEX IF NOT EXISTS social_posts_created ON social_posts(created_at);
            CREATE INDEX IF NOT EXISTS social_comments_post ON social_comments(post_id);
            ''')

    def settings(self, db, user_id):
        row = db.execute('SELECT * FROM social_settings WHERE user_id=?', (user_id,)).fetchone()
        return {key: bool(row[key]) if key != 'default_audience' else row[key] for key in ('accept_requests','sharing_enabled','default_audience','allow_comments')} if row else {'accept_requests':True,'sharing_enabled':True,'default_audience':'private','allow_comments':True}

    def privacy(self, user_id, data=None):
        with self.connection() as db:
            if data is not None:
                db.execute('INSERT INTO social_settings VALUES (?,?,?,?,?) ON CONFLICT(user_id) DO UPDATE SET accept_requests=excluded.accept_requests,sharing_enabled=excluded.sharing_enabled,default_audience=excluded.default_audience,allow_comments=excluded.allow_comments', (user_id,data['accept_requests'],data['sharing_enabled'],data['default_audience'],data['allow_comments']))
            return self.settings(db,user_id)

    @staticmethod
    def blocked(db, a, b):
        return bool(db.execute('SELECT 1 FROM social_blocks WHERE (blocker=? AND blocked=?) OR (blocker=? AND blocked=?)',(a,b,b,a)).fetchone())

    @staticmethod
    def friends(db,a,b):
        return bool(db.execute("SELECT 1 FROM friendships WHERE status='accepted' AND ((sender=? AND recipient=?) OR (sender=? AND recipient=?))",(a,b,b,a)).fetchone())

    def connections(self, uid):
        with self.connection() as db:
            rows=db.execute('''SELECT f.*, u.display_name,u.id FROM friendships f JOIN users u ON u.id=CASE WHEN sender=? THEN recipient ELSE sender END WHERE (sender=? OR recipient=?) AND u.active=1 ORDER BY created_at DESC''',(uid,uid,uid)).fetchall()
            blocks=db.execute('SELECT u.id,u.display_name FROM social_blocks b JOIN users u ON u.id=b.blocked WHERE b.blocker=?',(uid,)).fetchall()
            return {'connections':[dict(row) for row in rows if not self.blocked(db,uid,row['id'])], 'blocked':[dict(row) for row in blocks]}

    def request_friend(self,uid,target):
        if uid==target:
            raise ValueError('You cannot add yourself')
        with self.connection() as db:
            db.execute('BEGIN IMMEDIATE')
            if not db.execute('SELECT 1 FROM users WHERE id=? AND active=1',(target,)).fetchone() or self.blocked(db,uid,target) or not self.settings(db,target)['accept_requests']:
                raise LookupError('This person is unavailable for friend requests')
            if db.execute('SELECT 1 FROM friendships WHERE (sender=? AND recipient=?) OR (sender=? AND recipient=?)',(uid,target,target,uid)).fetchone():
                raise ValueError('A connection or request already exists')
            db.execute("INSERT INTO friendships VALUES (?,?,'pending',?)",(uid,target,int(time.time())))

    def accept(self,uid,sender):
        with self.connection() as db:
            if self.blocked(db,uid,sender):
                raise LookupError('Request not found')
            if db.execute("UPDATE friendships SET status='accepted' WHERE sender=? AND recipient=? AND status='pending'",(sender,uid)).rowcount==0:
                raise LookupError('Request not found')

    def remove(self,uid,target):
        with self.connection() as db:
            db.execute('DELETE FROM friendships WHERE (sender=? AND recipient=?) OR (sender=? AND recipient=?)',(uid,target,target,uid))

    def block(self,uid,target,enabled):
        if uid==target:
            raise ValueError('You cannot block yourself')
        with self.connection() as db:
            if not db.execute('SELECT 1 FROM users WHERE id=?',(target,)).fetchone():
                raise LookupError('User not found')
            if enabled:
                db.execute('INSERT OR IGNORE INTO social_blocks VALUES (?,?)',(uid,target))
                db.execute('DELETE FROM friendships WHERE (sender=? AND recipient=?) OR (sender=? AND recipient=?)',(uid,target,target,uid))
            else:
                db.execute('DELETE FROM social_blocks WHERE blocker=? AND blocked=?',(uid,target))

    def visible_post(self,db,uid,pid):
        row=db.execute('SELECT p.*,u.display_name FROM social_posts p JOIN users u ON u.id=p.user_id WHERE p.id=? AND u.active=1',(pid,)).fetchone()
        if row is None:
            raise LookupError('Activity not found')
        settings=self.settings(db,row['user_id'])
        if not can_view(owner=row['user_id'], viewer=uid, audience=row['audience'], sharing_enabled=settings['sharing_enabled'], friends=self.friends(db,uid,row['user_id']), blocked=self.blocked(db,uid,row['user_id'])):
            raise LookupError('Activity not found')
        return row

    def serialize_post(self,db,uid,row):
        post=dict(row)
        post['likes']=db.execute('SELECT count(*) FROM social_likes WHERE post_id=?',(row['id'],)).fetchone()[0]
        post['liked']=bool(db.execute('SELECT 1 FROM social_likes WHERE post_id=? AND user_id=?',(row['id'],uid)).fetchone())
        comments=db.execute('SELECT c.id,c.user_id,c.text,c.created_at,u.display_name FROM social_comments c JOIN users u ON u.id=c.user_id WHERE c.post_id=? AND u.active=1 ORDER BY c.created_at DESC,c.id DESC LIMIT 20',(row['id'],)).fetchall()
        post['comments']=[dict(c) for c in reversed(comments) if not self.blocked(db,uid,c['user_id'])]
        post['allow_comments']=self.settings(db,row['user_id'])['allow_comments']
        return post

    def post(self,uid,pid):
        with self.connection() as db:
            return self.serialize_post(db,uid,self.visible_post(db,uid,pid))

    def feed(self,uid,offset=0):
        with self.connection() as db:
            # Filter before pagination so inaccessible private content does not displace visible posts.
            rows=db.execute('''SELECT p.*,u.display_name FROM social_posts p JOIN users u ON u.id=p.user_id
                LEFT JOIN social_settings s ON s.user_id=p.user_id
                WHERE u.active=1 AND (p.user_id=? OR (p.audience='friends' AND COALESCE(s.sharing_enabled,1)=1
                AND EXISTS(SELECT 1 FROM friendships f WHERE f.status='accepted' AND ((f.sender=? AND f.recipient=p.user_id) OR (f.recipient=? AND f.sender=p.user_id)))
                AND NOT EXISTS(SELECT 1 FROM social_blocks b WHERE (b.blocker=? AND b.blocked=p.user_id) OR (b.blocked=? AND b.blocker=p.user_id))))
                ORDER BY p.created_at DESC,p.id DESC LIMIT 21 OFFSET ?''',(uid,uid,uid,uid,uid,offset)).fetchall()
            return {'items':[self.serialize_post(db,uid,row) for row in rows[:20]],'has_more':len(rows)>20}

    def publish(self,uid,data):
        pid=str(uuid4())
        with self.connection() as db:
            if data['audience']=='friends' and not self.settings(db,uid)['sharing_enabled']:
                raise ValueError('Enable sharing in Privacy before posting to friends')
            db.execute('INSERT INTO social_posts VALUES (?,?,?,?,?,?)',(pid,uid,data['kind'],data['text'],data['audience'],int(time.time())))
        return self.post(uid,pid)

    def edit_post(self,uid,pid,audience=None):
        with self.connection() as db:
            row=self.visible_post(db,uid,pid)
            if row['user_id']!=uid:
                raise LookupError('Activity not found')
            if audience is None:
                db.execute('DELETE FROM social_posts WHERE id=?',(pid,))
            else:
                if audience=='friends' and not self.settings(db,uid)['sharing_enabled']:
                    raise ValueError('Enable sharing in Privacy first')
                db.execute('UPDATE social_posts SET audience=? WHERE id=?',(audience,pid))

    def like(self,uid,pid,enabled):
        with self.connection() as db:
            self.visible_post(db,uid,pid)
            if enabled: db.execute('INSERT OR IGNORE INTO social_likes VALUES (?,?)',(pid,uid))
            else: db.execute('DELETE FROM social_likes WHERE post_id=? AND user_id=?',(pid,uid))

    def comment(self,uid,pid,text):
        with self.connection() as db:
            row=self.visible_post(db,uid,pid)
            if not self.settings(db,row['user_id'])['allow_comments']:
                raise ValueError('Comments are disabled for this activity')
            db.execute('INSERT INTO social_comments VALUES (?,?,?,?,?)',(str(uuid4()),pid,uid,text,int(time.time())))

    def delete_comment(self,uid,pid,cid):
        with self.connection() as db:
            post=self.visible_post(db,uid,pid)
            comment=db.execute('SELECT * FROM social_comments WHERE id=? AND post_id=?',(cid,pid)).fetchone()
            if not comment or (comment['user_id']!=uid and post['user_id']!=uid):
                raise LookupError('Comment not found')
            db.execute('DELETE FROM social_comments WHERE id=?',(cid,))

    def stats(self,uid):
        with self.connection() as db:
            total=lambda sql:db.execute(sql,(uid,)).fetchone()[0]
            return {'friends':total("SELECT count(*) FROM friendships f JOIN users u ON u.id=CASE WHEN f.sender=?1 THEN f.recipient ELSE f.sender END WHERE f.status='accepted' AND (f.sender=?1 OR f.recipient=?1) AND u.active=1"),
                    'pending_requests':total("SELECT count(*) FROM friendships f JOIN users u ON u.id=f.sender WHERE f.status='pending' AND f.recipient=? AND u.active=1"),
                    'activities':total('SELECT count(*) FROM social_posts WHERE user_id=?'),
                    'shared_activities':total("SELECT count(*) FROM social_posts WHERE user_id=? AND audience='friends'"),
                    'likes_received':total('SELECT count(*) FROM social_likes l JOIN social_posts p ON p.id=l.post_id WHERE p.user_id=? AND l.user_id!=p.user_id'),
                    'comments_received':total('SELECT count(*) FROM social_comments c JOIN social_posts p ON p.id=c.post_id WHERE p.user_id=? AND c.user_id!=p.user_id')}
