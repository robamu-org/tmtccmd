import enum
from typing import Deque, Tuple, List
from tmtccmd.ecss.tm import PusTelemetry

TelemetryListT = List[bytearray]
TelemetryQueueT = Deque[bytearray]

PusTmQueue = Deque[PusTelemetry]
PusTmTupleT = Tuple[bytearray, PusTelemetry]

PusTmListT = List[PusTelemetry]
PusTmQueueT = Deque[PusTmListT]

PusTmListT = List[PusTelemetry]
PusTmObjQeue = Deque[PusTelemetry]
PusTmTupleQueueT = Deque[PusTmTupleT]


class TmTypes(enum.Enum):
    NONE = enum.auto()
    CCSDS_SPACE_PACKETS = enum.auto()
