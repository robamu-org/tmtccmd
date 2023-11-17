import dataclasses
import enum
from typing import Optional, Dict


class Severity(enum.IntEnum):
    INFO = 1
    LOW = (2,)
    MEDIUM = (3,)
    HIGH = 4


def str_to_severity(string: str) -> Optional[Severity]:
    if string == "INFO":
        return Severity.INFO
    elif string == "LOW":
        return Severity.LOW
    elif string == "MEDIUM":
        return Severity.MEDIUM
    elif string == "HIGH":
        return Severity.HIGH


@dataclasses.dataclass
class EventInfo:
    id: int = 0
    name: str = ""
    severity: str = ""
    info: str = ""
    file_location: str = ""


EventDictT = Dict[int, EventInfo]
