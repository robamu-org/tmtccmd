import abc
from collections import deque
from typing import Dict

from tmtccmd.tm.handler import TmHandlerBase
from tmtccmd.tm.definitions import TmTypes
from tmtccmd.logging import get_console_logger

LOGGER = get_console_logger()


class ApidTmHandlerBase:
    """Handler base for space packets with an APID. If a packet is received for a certain APID,
    the :py:func:`handle_tm_for_apid` function will be called"""

    def __init__(self, apid: int, user_args: any):
        self.apid = apid
        self.user_args: any = user_args

    @abc.abstractmethod
    def handle_tm(self, _packet: bytes, _user_args: any):
        LOGGER.warning(f"No TM handling implemented for APID {self.apid}")


class UnknownApidHandlerBase:
    def __init__(self, max_queue_len: int, user_args: any):
        self.queue = deque(maxlen=max_queue_len)
        self.user_args: any = user_args

    @abc.abstractmethod
    def handle_tm(self, apid: int, _packet: bytes, _user_args: any):
        LOGGER.warning(f"No TM handling implemented for unknown APID {apid}")


HandlerDictT = Dict[int, ApidTmHandlerBase]


class CcsdsTmHandler(TmHandlerBase):
    """Generic CCSDS handler class. The user can create an instance of this class to handle
    CCSDS packets with different APIDs"""

    def __init__(self, unknown_handler: UnknownApidHandlerBase):
        super().__init__(tm_type=TmTypes.CCSDS_SPACE_PACKETS)
        self._handler_dict: HandlerDictT = dict()
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
