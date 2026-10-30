"""Password and account use cases. Session secrets are never stored raw."""
import hashlib
import secrets
import time
from uuid import uuid4

from posturepal.users.domain.models import User


def hash_password(password):
    salt = secrets.token_hex(16)
    digest = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=5).hex()
    return f'scrypt${salt}${digest}'


def verify_password(password, encoded):
    _, salt, digest = encoded.split('$')
    candidate = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=5).hex()
    return secrets.compare_digest(candidate, digest)


def digest_token(token):
    return hashlib.sha256(token.encode()).hexdigest()


class Accounts:
    def __init__(self, repository):
        self.repository = repository
        self.dummy_hash = hash_password(secrets.token_urlsafe(32))

    def create(self, email, name, password, role='member'):
        user = User(str(uuid4()), email.lower(), name, '', 'UTC', 'light', role, True, int(time.time()))
        return self.repository.create(user, hash_password(password))

    def login(self, email, password):
        row = self.repository.credentials(email.lower())
        valid = verify_password(password, row['password_hash'] if row else self.dummy_hash)
        if not row or not valid or not row['active']:
            raise PermissionError('Invalid email or password')
        token = secrets.token_urlsafe(48)
        now = int(time.time())
        self.repository.add_session(digest_token(token), row['id'], now + 43200, now)
        return token, self.repository.public(row)

    def authenticate(self, token):
        return self.repository.session(digest_token(token), int(time.time())) if token else None

    def check_password(self, user, password):
        row = self.repository.credentials(user.email)
        if not row or not verify_password(password, row['password_hash']):
            raise PermissionError('Current password is incorrect')
