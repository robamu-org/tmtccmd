import enum
import abc
import logging
from typing import Deque, List, Any, Dict, Optional
from spacepackets.ecss.tm import PusTelemetry


TelemetryListT = List[bytes]
TelemetryQueueT = Deque[bytes]

PusTmQueue = Deque[PusTelemetry]
PusTmListT = List[PusTelemetry]

PusTmQueueT = Deque[PusTmListT]


class SpecificApidHandlerBase(abc.ABC):
    """Abstract base class for an CCSDS APID specific handler. The user can implement a TM handler
    by implementing this class and then adding it to the :py:class:`CcsdsTmHandler`.
    If a CCSDS space packet with a specific APID is received, it will be routed to this handler
    using the :py:func:`handle_tm` callback function
    """

    def __init__(self, apid: int, user_args: Any):
        self.apid = apid
        self.user_args: Any = user_args

    @abc.abstractmethod
    def handle_tm(self, _packet: bytes, _user_args: Any):
        logging.getLogger(__name__).warning(
            f"No TM handling implemented for APID {self.apid}"
        )


class GenericApidHandlerBase(abc.ABC):
    """This class is similar to the :py:class:`SpecificApidHandlerBase` but it is not specific
    for an APID and the found APID will be passed to the callback
    """

    def __init__(self, user_args: Any):
        self.user_args: Any = user_args

    @abc.abstractmethod
    def handle_tm(self, apid: int, _packet: bytes, _user_args: Any):
        pass


class DefaultApidHandler(GenericApidHandlerBase):
    def handle_tm(self, apid: int, _packet: bytes, _user_args: Any):
        logging.getLogger(__name__).warning(
            f"No TM handling implemented for unknown APID {apid}"
        )


HandlerDictT = Dict[int, SpecificApidHandlerBase]


class TmTypes(enum.Enum):
    NONE = enum.auto
    CCSDS_SPACE_PACKETS = enum.auto


class TmHandlerBase:
    def __init__(self, tm_type: TmTypes):
        self._tm_type = tm_type

    def get_type(self):
        return self._tm_type


class CcsdsTmHandler(TmHandlerBase):
    """Generic CCSDS handler class. The user can create an instance of this class to handle
    CCSDS packets by adding dedicated APID handlers or a generic handler for all APIDs with no
    dedicated handler"""

    def __init__(self, generic_handler: Optional[GenericApidHandlerBase]):
        super().__init__(tm_type=TmTypes.CCSDS_SPACE_PACKETS)
        self._handler_dict: HandlerDictT = dict()
        if generic_handler is None:
            self.generic_handler = DefaultApidHandler(None)
        else:
            self.generic_handler = generic_handler

    def add_apid_handler(self, handler: SpecificApidHandlerBase):
        """Add a TM handler for a certain APID. The handler is a callback function which
        will be called if telemetry with that APID arrives.

        :param handler: Handler class instance
        :return:
        """
        self._handler_dict[handler.apid] = handler

    def has_apid(self, apid: int) -> bool:
        return apid in self._handler_dict

    def user_hook(self, apid: int, packet: bytes):
        """Can be overriden to trace all packets received."""
        pass

    def handle_packet(self, apid: int, packet: bytes) -> bool:
        """Handle a packet with an APID. If a handler exists for the given APID,
        it is used to handle the packet. If not, a dedicated handler for unknown APIDs
        is called.

        :param apid:
        :param packet:
        :return: True if the packet was passed to as dedicated APID handler, False otherwise
        """
        self.user_hook(apid, packet)
        specific_handler = self._handler_dict.get(apid)
        if specific_handler is None:
            self.generic_handler.handle_tm(apid, packet, self.generic_handler.user_args)
            return False
        specific_handler.handle_tm(packet, specific_handler.user_args)
        return True
