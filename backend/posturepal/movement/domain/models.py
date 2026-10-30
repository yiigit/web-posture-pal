from dataclasses import dataclass
from typing import Protocol

@dataclass(frozen=True)
class Exercise:
    id: str
    name: str
    area: str
    duration: int
    description: str
    steps: tuple[str, ...]
    position: str
    symbol: str

class ExerciseRepository(Protocol):
    def all(self) -> list[Exercise]: ...

    def create(self, exercise: Exercise) -> Exercise: ...
    def update(self, exercise: Exercise) -> Exercise: ...
    def delete(self, exercise_id: str) -> None: ...


class DuplicateExercise(Exception):
    pass


class MissingExercise(Exception):
    pass
