import dataclasses
import enum
from typing import Optional


class Severity(enum.IntEnum):
    INFO = 1
    LOW = 2
    MEDIUM = 3
    HIGH = 4

STR_TO_SEVERITY = {
    "INFO": Severity.INFO,
    "LOW": Severity.LOW,
    "MEDIUM": Severity.MEDIUM,
    "HIGH": Severity.HIGH,
}


def str_to_severity(string: str) -> Optional[Severity]:
    STR_TO_SEVERITY.get(string)


@dataclasses.dataclass
class EventInfo:
    id: int = 0
    name: str = ""
    severity: str = ""
    info: str = ""
    file_location: str = ""


EventDictT = dict[int, EventInfo]
