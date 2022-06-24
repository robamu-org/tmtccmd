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

    def __init__(self, queue_len: int, user_args: any):
        self.queue_len: int = queue_len
        self.queue = deque(maxlen=queue_len)
        self.user_args: any = user_args

    @abc.abstractmethod
    def handle_tm_for_apid(self, apid: int, packet: bytes, user_args: any):
        pass


HandlerDictT = Dict[int, ApidTmHandlerBase]


class CcsdsTmHandler(TmHandlerBase):
    """Generic CCSDS handler class. The user can create an instance of this class to handle
    CCSDS packets with different APIDs"""

    def __init__(self):
        super().__init__(tm_type=TmTypes.CCSDS_SPACE_PACKETS)
        self._handler_dict: HandlerDictT = dict()

    def add_apid_handler(self, apid: int, handler: ApidTmHandlerBase):
        """Add a TM handler for a certain APID. The handler is a callback function which
        will be called if telemetry with that APID arrives
        :param apid: CCSDS Application Process ID
        :param handler: Handler class instance
        :return:
        """
        self._handler_dict[apid] = handler

    def handle_packet(self, apid: int, packet: bytes) -> bool:
        handler = self._handler_dict.get(apid)
        if handler is None:
            return False
        else:
            handler.handle_tm_for_apid(apid, packet, handler.user_args)
