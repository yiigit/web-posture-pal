from dataclasses import dataclass


@dataclass(frozen=True)
class User:
    id: str
    email: str
    display_name: str
    bio: str
    timezone: str
    theme: str
    role: str
    active: bool
    created_at: int


class DuplicateEmail(ValueError):
    pass
