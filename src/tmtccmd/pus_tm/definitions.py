from typing import Deque, Tuple, List
from tmtccmd.ecss.tm import PusTelemetry

PusTmQueue = Deque[PusTelemetry]
PusTmTupleT = Tuple[bytearray, PusTelemetry]

TelemetryListT = List[bytearray]
TelemetryQueueT = Deque[TelemetryListT]

PusTmListT = List[PusTelemetry]
PusTmQueueT = Deque[PusTmListT]

PusTmListT = List[PusTelemetry]
PusTmObjQeue = Deque[PusTelemetry]
PusTmTupleQueueT = Deque[PusTmTupleT]
