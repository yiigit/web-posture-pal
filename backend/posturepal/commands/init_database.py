"""Create missing tables and initialize the catalog without starting the server."""
import argparse
import os
from pathlib import Path
import re

from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL, make_url

from posturepal.movement.infrastructure.repository import ExerciseRepository
from posturepal.shared.infrastructure.database import Database


class ConfigurationError(ValueError):
    """Messages contain only fixed text and known configuration field names."""


def failure_message(error):
    if isinstance(error, ConfigurationError):
        return str(error)
    if isinstance(error, FileNotFoundError):
        return 'Configuration file not found; create .env or check --env-file.'
    if isinstance(error, PermissionError):
        return 'Cannot read the configuration file; check file ownership and permissions.'
    original = getattr(error, 'orig', error)
    code = original.args[0] if original.args else None
    messages = {
        1044: 'Database access denied. Ask the MySQL administrator to grant this user privileges on the intended database.',
        1045: 'MySQL login rejected. Check MYSQL_USER, MYSQL_PASSWORD and the account host grants.',
        1049: 'Database does not exist. Create it or enable --create-database with a suitably privileged user.',
        1142: 'MySQL operation denied. Check table creation and application read/write permissions.',
        1143: 'MySQL column access denied. Check application database permissions.',
        2002: 'Cannot reach MySQL. Check its service, MYSQL_HOST, MYSQL_PORT and network access.',
        2003: 'Cannot reach MySQL. Check its service, MYSQL_HOST, MYSQL_PORT and network access.',
        2005: 'MySQL hostname cannot be resolved. For native local MySQL, set MYSQL_HOST=127.0.0.1 rather than the Docker hostname mysql.',
        2026: 'MySQL TLS connection failed. Check certificate and TLS connection settings.',
        1146: 'A required table is missing. Check schema initialization and database permissions.',
        1054: 'Existing table columns do not match the application schema; a schema migration may be needed.',
    }
    if type(code) is int:
        return f'MySQL error {code}: ' + messages.get(code, 'Check server status, schema compatibility and database permissions.')
    if isinstance(error, (ValueError, TypeError)):
        return 'Invalid configuration. Check connection URL syntax, numeric port and literal dotenv assignments.'
    return 'Check MySQL availability, installed requirements and database permissions.'


def initialize(database):
    """Reuse the catalog's transactional, once-only initialization."""
    ExerciseRepository(database)
    with database.connection() as connection:
        connection.execute('SELECT 1').fetchone()


def load_environment(path):
    """Read literal dotenv assignments; never evaluate shell code or substitutions."""
    values = {}
    for line in Path(path).read_text().splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        key, separator, value = line.partition('=')
        key, value = key.strip(), value.strip()
        if not separator or not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', key):
            raise ConfigurationError('Invalid .env assignment; use literal KEY=value lines.')
        if value.startswith(('"', "'")):
            if len(value) < 2 or value[-1] != value[0]:
                raise ConfigurationError('Unmatched quotes in .env; use matching outer quotes.')
            value = value[1:-1]
        values[key] = value
    for key, value in values.items():
        os.environ.setdefault(key, value)


def mysql_url():
    if os.getenv('POSTUREPAL_DATABASE_URL'):
        url = make_url(os.environ['POSTUREPAL_DATABASE_URL'])
    else:
        missing = [key for key in ('MYSQL_HOST', 'MYSQL_USER', 'MYSQL_PASSWORD', 'MYSQL_DATABASE') if not os.getenv(key)]
        if missing:
            raise ConfigurationError('Missing required settings: ' + ', '.join(missing) + '. Set them in .env or the shell.')
        url = URL.create('mysql+pymysql', username=os.environ['MYSQL_USER'],
                         password=os.environ['MYSQL_PASSWORD'], host=os.environ['MYSQL_HOST'],
                         port=int(os.getenv('MYSQL_PORT', '3306')),
                         database=os.environ['MYSQL_DATABASE'], query={'charset': 'utf8mb4'})
    if url.drivername != 'mysql+pymysql' or not url.host or not url.database:
        raise ConfigurationError('Use an explicit mysql+pymysql connection with a host and database; SQLite is not supported by this command.')
    if url.port is not None and not 1 <= url.port <= 65535:
        raise ConfigurationError('MYSQL_PORT must be between 1 and 65535.')
    return url


def create_database(url):
    # Identifiers cannot be bound parameters; restrict the database name first.
    if not re.fullmatch(r'[A-Za-z0-9_]{1,64}', url.database):
        raise ConfigurationError('Database name must contain 1–64 letters, digits or underscores.')
    engine = create_engine(url.set(database=''), hide_parameters=True)
    try:
        with engine.begin() as connection:
            connection.execute(text(f'CREATE DATABASE IF NOT EXISTS `{url.database}` '
                                    'CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci'))
    finally:
        engine.dispose()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--env-file', help='Literal dotenv file; shell environment takes precedence')
    parser.add_argument('--create-database', action='store_true', help='Create missing MySQL database before tables')
    args = parser.parse_args()
    database = None
    stage = 'loading configuration'
    try:
        if args.env_file:
            load_environment(args.env_file)
        url = mysql_url()
        if args.create_database:
            stage = 'creating the MySQL database'
            create_database(url)
        stage = 'connecting and creating application tables'
        database = Database(url)
        stage = 'initializing the movement catalog'
        initialize(database)
    except Exception as error:
        # Connection/SQL exceptions can contain credentials or private records.
        raise SystemExit(f'Database initialization failed while {stage}. {failure_message(error)}') from None
    finally:
        if database is not None:
            database.engine.dispose()
    print('Database tables and standard catalog are ready. Existing data preserved.')


if __name__ == '__main__':
    main()
