from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Union


class Status(Enum):
    OK = "ok"
    SKIP = "skip"
    CONFLICT = "conflict"
    NOT_FOUND = "not_found"
    INVALID = "invalid"
    ERROR = "error"
    ALLOW = "allow"
    REJECT = "reject"


ContentType = Union[str, dict, Path]


@dataclass(slots=True)
class Output:
    status: Status
    content: ContentType | None = None
