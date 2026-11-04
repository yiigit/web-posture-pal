"""Native database setup checks use temporary SQLite and mocked MySQL only."""
import os
from pathlib import Path
import tempfile
import shutil
import subprocess
import unittest
from unittest.mock import MagicMock, patch

from posturepal.commands.init_database import create_database, failure_message, initialize, load_environment, main, mysql_url
from sqlalchemy.exc import OperationalError
from posturepal.shared.infrastructure.database import Database
from sqlalchemy.engine import URL


class DatabaseSetupTests(unittest.TestCase):
    def test_mysql_diagnostics_do_not_reveal_exception_details(self):
        for code, expected in ((1045, 'login rejected'), (1044, 'access denied'),
                               (2003, 'Cannot reach'), (2005, '127.0.0.1'),
                               (2026, 'TLS'), (9999, 'server status')):
            with self.subTest(code=code):
                error = OperationalError('private SQL', {'password': 'private-password'},
                                         Exception(code, 'private exception detail'))
                message = failure_message(error)
                self.assertIn(expected, message)
                self.assertIn(str(code), message)
                self.assertNotIn('private', message)
        self.assertNotIn('secret', failure_message(RuntimeError('secret')))

    def test_cli_reports_stage_without_private_details(self):
        with patch('sys.argv', ['init_database', '--create-database']), \
                patch('posturepal.commands.init_database.mysql_url', return_value=MagicMock()), \
                patch('posturepal.commands.init_database.create_database', side_effect=Exception(1045, 'secret')):
            with self.assertRaises(SystemExit) as caught:
                main()
            self.assertIn('creating the MySQL database', str(caught.exception))
            self.assertIn('login rejected', str(caught.exception))
            self.assertNotIn('secret', str(caught.exception))

    def test_launcher_reports_missing_deployment_module(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            scripts = Path(directory) / 'scripts'
            scripts.mkdir()
            launcher = scripts / 'setup_database.sh'
            shutil.copyfile(root / 'scripts/setup_database.sh', launcher)
            result = subprocess.run(['bash', str(launcher)], cwd='/tmp',
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 1)
            self.assertIn('init_database.py is missing', result.stderr)
            self.assertNotIn('No module named', result.stderr)

    def test_literal_configuration_and_environment_precedence(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {'MYSQL_HOST': 'existing'}, clear=True):
            path = Path(directory) / 'config'
            path.write_text('MYSQL_HOST=ignored\nMYSQL_PASSWORD=\'literal$()#secret\'\n')
            load_environment(path)
            self.assertEqual(os.environ['MYSQL_HOST'], 'existing')
            self.assertEqual(os.environ['MYSQL_PASSWORD'], 'literal$()#secret')

    def test_only_explicit_mysql_is_allowed(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ValueError):
                mysql_url()
        with patch.dict(os.environ, {'POSTUREPAL_DATABASE_URL': 'sqlite:///test.db'}, clear=True):
            with self.assertRaises(ValueError):
                mysql_url()
        with patch.dict(os.environ, {'MYSQL_HOST': '127.0.0.1', 'MYSQL_USER': 'app',
                                   'MYSQL_PASSWORD': 'test-only', 'MYSQL_DATABASE': 'posturepal'}, clear=True):
            self.assertEqual(mysql_url().drivername, 'mysql+pymysql')

    def test_create_database_and_close_connection(self):
        engine = MagicMock()
        url = URL.create('mysql+pymysql', host='localhost', database='posturepal')
        with patch('posturepal.commands.init_database.create_engine', return_value=engine) as factory:
            create_database(url)
            self.assertEqual(factory.call_args.args[0].database, '')
            sql = engine.begin.return_value.__enter__.return_value.execute.call_args.args[0]
            self.assertIn('CREATE DATABASE IF NOT EXISTS `posturepal`', str(sql))
            engine.dispose.assert_called_once()
            with self.assertRaises(ValueError):
                create_database(url.set(database='invalid`; DROP DATABASE other'))
            self.assertEqual(factory.call_count, 1)

    def test_catalog_is_seeded_once(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Database.from_path(Path(directory) / 'test.db')
            try:
                initialize(database)
                with database.connection() as connection:
                    self.assertEqual(connection.execute('SELECT COUNT(*) FROM exercises').fetchone()[0], 8)
                    connection.execute('DELETE FROM exercises')
                initialize(database)
                with database.connection() as connection:
                    self.assertEqual(connection.execute('SELECT COUNT(*) FROM exercises').fetchone()[0], 0)
                    self.assertEqual(connection.execute('SELECT COUNT(*) FROM users').fetchone()[0], 0)
            finally:
                database.engine.dispose()

    def test_errors_are_sanitized(self):
        with patch('sys.argv', ['init_database']), patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(SystemExit) as caught:
                main()
            self.assertNotIn('Traceback', str(caught.exception))
