import enum
from typing import Deque, List, Union

from spacepackets.ecss import PusTelemetry
from tmtccmd.tm.base import PusTmInfoInterface, PusTmInterface
from tmtccmd.tm.pus_5_event import Service5Tm
from tmtccmd.tm.pus_8_funccmd import Service8FsfwTm
from tmtccmd.tm.pus_3_fsfw_hk import Service3FsfwTm
from tmtccmd.tm.pus_20_fsfw_parameters import Service20FsfwTm
from tmtccmd.tm.pus_200_fsfw_modes import Service200FsfwTm

TelemetryListT = List[bytes]
TelemetryQueueT = Deque[bytes]

PusTmQueue = Deque[PusTelemetry]
PusTmListT = List[PusTelemetry]

PusTmQueueT = Deque[PusTmListT]
PusIFListT = List[Union[PusTmInfoInterface, PusTmInterface]]
PusIFQueueT = Deque[PusIFListT]


class TmTypes(enum.Enum):
    NONE = enum.auto
    CCSDS_SPACE_PACKETS = enum.auto


class TmHandlerBase:
    def __init__(self, tm_type: TmTypes):
        self._tm_type = tm_type

    def get_type(self):
        return self._tm_type
