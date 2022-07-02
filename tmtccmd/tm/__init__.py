import enum
from abc import abstractmethod, ABC
from typing import Deque, List, Union, Dict, Optional

from spacepackets.ecss import PusTelemetry
from tmtccmd.logging import get_console_logger
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


LOGGER = get_console_logger()


class TmTypes(enum.Enum):
    NONE = enum.auto
    CCSDS_SPACE_PACKETS = enum.auto


class TmHandlerBase:
    def __init__(self, tm_type: TmTypes):
        self._tm_type = tm_type

    def get_type(self):
        return self._tm_type


class ApidTmHandlerBase(ABC):
    """Handler base for space packets with an APID. If a packet is received for a certain APID,
    the :py:func:`handle_tm` function will be called"""

    def __init__(self, apid: int, user_args: any):
        self.apid = apid
        self.user_args: any = user_args

    @abstractmethod
    def handle_tm(self, _packet: bytes, _user_args: any):
        LOGGER.warning(f"No TM handling implemented for APID {self.apid}")


class UnknownApidHandlerBase(ABC):
    def __init__(self, user_args: any):
        self.user_args: any = user_args

    @abstractmethod
    def handle_tm(self, apid: int, _packet: bytes, _user_args: any):
        pass


class DefaultUnknownHandler(UnknownApidHandlerBase):
    def handle_tm(self, apid: int, _packet: bytes, _user_args: any):
        LOGGER.warning(f"No TM handling implemented for unknown APID {apid}")


HandlerDictT = Dict[int, ApidTmHandlerBase]


class CcsdsTmHandler(TmHandlerBase):
    """Generic CCSDS handler class. The user can create an instance of this class to handle
    CCSDS packets with different APIDs"""

    def __init__(self, unknown_handler: Optional[UnknownApidHandlerBase]):
        super().__init__(tm_type=TmTypes.CCSDS_SPACE_PACKETS)
        self._handler_dict: HandlerDictT = dict()
        if unknown_handler is None:
            self.unknown_handler = DefaultUnknownHandler(None)
        else:
            self.unknown_handler = unknown_handler

    def add_apid_handler(self, handler: ApidTmHandlerBase):
        """Add a TM handler for a certain APID. The handler is a callback function which
        will be called if telemetry with that APID arrives
        :param handler: Handler class instance
        :return:
        """
        self._handler_dict[handler.apid] = handler

    def has_apid(self, apid: int) -> bool:
        return apid in self._handler_dict

    def handle_packet(self, apid: int, packet: bytes) -> bool:
        """Handle a packet with an APID. If a handler exists for the given APID,
        it is used to handle the packet. If not, a dedicated handler for unknown APIDs
        is called.

        :param apid:
        :param packet:
        :return: True if the packet was passed to as dedicated APID handler, False otherwise
        """
        handler = self._handler_dict.get(apid)
        if handler is None:
            self.unknown_handler.handle_tm(apid, packet, self.unknown_handler.user_args)
            return False
        handler.handle_tm(packet, handler.user_args)
        return True
