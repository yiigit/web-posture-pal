"""Durable catalog storage; each operation owns its connection/transaction."""
import json
from sqlalchemy.exc import IntegrityError
from posturepal.shared.infrastructure.database import Database
from dataclasses import astuple
from pathlib import Path

from posturepal.movement.domain.models import Exercise, DuplicateExercise, MissingExercise
from posturepal.movement.infrastructure.catalog import CatalogRepository


class ExerciseRepository:
    def __init__(self, database):
        self.database = database if isinstance(database, Database) else Database.from_path(database)
        self.connection = self.database.connection
        with self.connection() as db:
            db.lock()
            if not db.execute("SELECT 1 FROM metadata WHERE `key` = 'seeded'").fetchone():
                for item in CatalogRepository().all():
                    db.insert_once('exercises', dict(zip(('id','name','area','duration','description','steps','position','symbol'), self.values(item))))
                db.execute("INSERT INTO metadata (`key`) VALUES ('seeded')")

    @staticmethod
    def values(item):
        values = list(astuple(item))
        values[5] = json.dumps(item.steps)
        return values

    def all(self):
        with self.connection() as db:
            rows = db.execute('SELECT * FROM exercises ORDER BY id').fetchall()
        return [Exercise(*row[:5], tuple(json.loads(row[5])), *row[6:]) for row in rows]

    def create(self, exercise):
        try:
            with self.connection() as db:
                db.execute('INSERT INTO exercises VALUES (?,?,?,?,?,?,?,?)', self.values(exercise))
        except IntegrityError as error:
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


SQLiteExerciseRepository = ExerciseRepository
