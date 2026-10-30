"""Durable catalog storage; each operation owns its connection/transaction."""
import json
import sqlite3
from contextlib import contextmanager
from dataclasses import astuple
from pathlib import Path

from posturepal.movement.domain.models import Exercise, DuplicateExercise, MissingExercise
from posturepal.movement.infrastructure.catalog import CatalogRepository


class SQLiteExerciseRepository:
    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as db:
            db.execute('CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY)')
            db.execute('''CREATE TABLE IF NOT EXISTS exercises (
                id TEXT PRIMARY KEY, name TEXT NOT NULL, area TEXT NOT NULL,
                duration INTEGER NOT NULL CHECK(duration > 0), description TEXT NOT NULL,
                steps TEXT NOT NULL, position TEXT NOT NULL, symbol TEXT NOT NULL)''')
            db.execute('BEGIN IMMEDIATE')
            if not db.execute("SELECT 1 FROM metadata WHERE key = 'seeded'").fetchone():
                for item in CatalogRepository().all():
                    db.execute('INSERT OR IGNORE INTO exercises VALUES (?,?,?,?,?,?,?,?)', self.values(item))
                db.execute("INSERT INTO metadata VALUES ('seeded')")

    @contextmanager
    def connection(self):
        db = sqlite3.connect(self.path, timeout=10)
        try:
            with db:
                yield db
        finally:
            db.close()

    @staticmethod
    def values(item):
        values = list(astuple(item))
        values[5] = json.dumps(item.steps)
        return values

    def all(self):
        with self.connection() as db:
            rows = db.execute('SELECT * FROM exercises ORDER BY rowid').fetchall()
        return [Exercise(*row[:5], tuple(json.loads(row[5])), *row[6:]) for row in rows]

    def create(self, exercise):
        try:
            with self.connection() as db:
                db.execute('INSERT INTO exercises VALUES (?,?,?,?,?,?,?,?)', self.values(exercise))
        except sqlite3.IntegrityError as error:
            raise DuplicateExercise from error
        return exercise

    def update(self, exercise):
        values = self.values(exercise)
        with self.connection() as db:
            result = db.execute('''UPDATE exercises SET name=?,area=?,duration=?,description=?,
                                steps=?,position=?,symbol=? WHERE id=?''', values[1:] + values[:1])
            if result.rowcount == 0:
                raise MissingExercise
        return exercise

    def delete(self, exercise_id):
        with self.connection() as db:
            if db.execute('DELETE FROM exercises WHERE id=?', (exercise_id,)).rowcount == 0:
                raise MissingExercise
