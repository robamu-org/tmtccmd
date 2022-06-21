import abc
from typing import Dict, Optional, Tuple, List

from tmtccmd.tm.handler import TmHandlerBase
from tmtccmd.tm.definitions import TelemetryQueueT, TmTypes
from tmtccmd.sendreceive.tm_listener import QueueListT
from tmtccmd.logging import get_console_logger

LOGGER = get_console_logger()


class ApidTmHandlerBase:
    """Handler base for space packets with an APID. If a packet is received for a certain APID,
    the :py:func:`handle_tm_for_apid` function will be called"""

    def __init__(self, queue_len: int, user_args: any):
        self.queue_len: int = queue_len
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

    def add_tm_handler(self, apid: int, handler: ApidTmHandlerBase):
        """Add a TM handler for a certain APID. The handler is a callback function which
        will be called if telemetry with that APID arrives
        :param apid: CCSDS Application Process ID
        :param handler: Handler class instance
        :return:
        """
        self._handler_dict[apid] = handler

    def get_apid_queue_len_list(self) -> List[Tuple[int, int]]:
        apid_queue_len_list = []
        for apid, handler_value in self._handler_dict.items():
            apid_queue_len_list.append((apid, handler_value.queue_len))
        return apid_queue_len_list

    def handle_packet_queues(self, packet_queue_list: QueueListT):
        for queue_tuple in packet_queue_list:
            apid = queue_tuple[0]
            self.handle_ccsds_packet_queue(
                tm_queue=queue_tuple[1], apid=apid, handler=self._handler_dict.get(apid)
            )

    def handle_ccsds_packet_queue(
        self,
        tm_queue: TelemetryQueueT,
        apid: int,
        handler: Optional[ApidTmHandlerBase],
    ):
        if handler is None:
            handler = self._handler_dict.get(apid)
        if handler is None:
            LOGGER.warning(f"No valid handler for TM with APID {apid} found")
        else:
            for tm_packet in tm_queue:
                handler.handle_tm_for_apid(apid, tm_packet, handler.user_args)
