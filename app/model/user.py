from dataclasses import dataclass, field
from typing import List


@dataclass(frozen=True)
class User:
    authenticated: bool = False
    email: str = 'anonymous'
    groups: List[str] = field(default_factory=list)
