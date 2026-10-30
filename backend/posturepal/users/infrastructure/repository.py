from sqlalchemy.exc import IntegrityError
from posturepal.shared.infrastructure.database import Database
from dataclasses import asdict

from posturepal.users.domain.models import User, DuplicateEmail


class UserRepository:
    def __init__(self, database):
        self.database = database if isinstance(database, Database) else Database.from_path(database)
        self.connection = self.database.connection

    @staticmethod
    def public(row):
        if row is None:
            return None
        return User(**{key: bool(row[key]) if key == 'active' else row[key] for key in User.__dataclass_fields__})

    def get(self, user_id):
        with self.connection() as db:
            return self.public(db.execute('SELECT * FROM users WHERE id=?', (user_id,)).fetchone())

    def credentials(self, email):
        with self.connection() as db:
            return db.execute('SELECT * FROM users WHERE email=?', (email,)).fetchone()

    def create(self, user, password_hash):
        try:
            with self.connection() as db:
                db.execute('INSERT INTO users VALUES (?,?,?,?,?,?,?,?,?,?)', (*asdict(user).values(), password_hash))
        except IntegrityError:
            raise DuplicateEmail('An account with that email already exists') from None
        return user

    def list(self, query, limit, offset):
        with self.connection() as db:
            rows = db.execute('SELECT * FROM users WHERE instr(lower(email),lower(?)) > 0 OR instr(lower(display_name),lower(?)) > 0 ORDER BY created_at DESC,id LIMIT ? OFFSET ?', (query, query, limit, offset)).fetchall()
            total = db.execute('SELECT count(*) FROM users WHERE instr(lower(email),lower(?)) > 0 OR instr(lower(display_name),lower(?)) > 0', (query, query)).fetchone()[0]
        return {'items': [self.public(row) for row in rows], 'total': total}

    def profile(self, user_id, data):
        with self.connection() as db:
            db.execute('UPDATE users SET display_name=?,bio=?,timezone=?,theme=? WHERE id=?', (data['display_name'], data['bio'], data['timezone'], data['theme'], user_id))
        return self.get(user_id)

    def access(self, user_id, role, active):
        with self.connection() as db:
            db.lock()
            old = db.execute('SELECT * FROM users WHERE id=?', (user_id,)).fetchone()
            if old is None:
                raise LookupError('User not found')
            self.protect_last_admin(db, old, role == 'admin' and active)
            db.execute('UPDATE users SET role=?,active=? WHERE id=?', (role, active, user_id))
            db.execute('DELETE FROM user_sessions WHERE user_id=?', (user_id,))
        return self.get(user_id)

    @staticmethod
    def protect_last_admin(db, old, remains_admin=False):
        if old['role'] == 'admin' and old['active'] and not remains_admin:
            if db.execute("SELECT count(*) FROM users WHERE role='admin' AND active=1").fetchone()[0] <= 1:
                raise ValueError('The last active administrator cannot be removed or disabled')

    def delete(self, user_id):
        with self.connection() as db:
            db.lock()
            old = db.execute('SELECT * FROM users WHERE id=?', (user_id,)).fetchone()
            if old is None:
                raise LookupError('User not found')
            self.protect_last_admin(db, old)
            db.execute('DELETE FROM users WHERE id=?', (user_id,))

    def password(self, user_id, password_hash):
        with self.connection() as db:
            db.execute('UPDATE users SET password_hash=? WHERE id=?', (password_hash, user_id))
            db.execute('DELETE FROM user_sessions WHERE user_id=?', (user_id,))

    def session(self, digest, now):
        with self.connection() as db:
            row = db.execute('SELECT u.* FROM users u JOIN user_sessions s ON u.id=s.user_id WHERE s.digest=? AND s.expires_at>? AND u.active=1', (digest, now)).fetchone()
        return self.public(row)

    def add_session(self, digest, user_id, expires_at, now):
        with self.connection() as db:
            db.execute('DELETE FROM user_sessions WHERE expires_at<=?', (now,))
            db.execute('INSERT INTO user_sessions VALUES (?,?,?)', (digest, user_id, expires_at))

    def revoke(self, digest):
        with self.connection() as db:
            db.execute('DELETE FROM user_sessions WHERE digest=?', (digest,))

    def attempt(self, key, now):
        with self.connection() as db:
            db.lock()
            db.execute('DELETE FROM auth_attempts WHERE expires_at<=?', (now,))
            row = db.execute('SELECT count FROM auth_attempts WHERE `key`=?', (key,)).fetchone()
            if row and row['count'] >= 10:
                return False
            if row:
                db.execute('UPDATE auth_attempts SET count=count+1 WHERE `key`=?', (key,))
            else:
                db.execute('INSERT INTO auth_attempts VALUES (?,1,?)', (key, now + 900))
        return True
