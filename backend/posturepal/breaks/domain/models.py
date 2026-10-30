from dataclasses import dataclass


@dataclass(frozen=True)
class BreakRoutine:
    id: str
    name: str
    description: str
    duration: int
    steps: tuple[str, ...]
    caution: str


@dataclass(frozen=True)
class PostureCheck:
    id: str
    name: str
    items: tuple[str, ...]


@dataclass(frozen=True)
class DailyHabit:
    id: str
    name: str
    cue: str
