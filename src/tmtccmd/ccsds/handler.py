from typing import Callable, Dict, Optional, Tuple, List, Type, Any

from tmtccmd.tm.handler import TmHandler
from tmtccmd.tm.definitions import TelemetryQueueT, TmTypes
from tmtccmd.sendreceive.tm_listener import QueueListT
from tmtccmd.utility.tmtc_printer import FsfwTmTcPrinter
from tmtccmd.logging import get_console_logger

LOGGER = get_console_logger()

CcsdsCallbackT = Callable[[int, bytes, Any], None]


class ApidHandler:
    def __init__(self, cb: CcsdsCallbackT, queue_len: int, user_args: any):
        self.callback: CcsdsCallbackT = cb
        self.queue_len: int = queue_len
        self.user_args: any = user_args


HandlerDictT = Dict[int, ApidHandler]


class CcsdsTmHandler(TmHandler):
    """Generic CCSDS handler class. The user can create an instance of this class to handle
    CCSDS packets with different APIDs"""

    def __init__(self):
        super().__init__(tm_type=TmTypes.CCSDS_SPACE_PACKETS)
        self._handler_dict: HandlerDictT = dict()

    def add_tm_handler(self, apid: int, handler: ApidHandler):
        """Add a TM handler for a certain APID. The handler is a callback function which
        will be called if telemetry with that APID arrives
        :param apid:            CCSDS Application Process ID
        :param pus_tm_handler:  Callback function
        :param max_queue_len:
        :return:
        """
        self._handler_dict[apid] = handler

    def get_apid_queue_len_list(self) -> List[Tuple[int, int]]:
        list = []
        for apid, handler_value in self._handler_dict.items():
            list.append((apid, handler_value.queue_len))
        return list

    def handle_packet_queues(self, packet_queue_list: QueueListT):
        for queue_tuple in packet_queue_list:
            apid = queue_tuple[0]
            handler_obj = self._handler_dict.get(apid)
            if handler_obj is not None:
                self.handle_ccsds_packet_queue(
                    queue=queue_tuple[1], apid=apid, handler=handler_obj
                )

    def handle_ccsds_packet_queue(
        self,
        tm_queue: TelemetryQueueT,
        apid: int,
        handler: Optional[ApidHandler] = None,
    ):
        if handler is None:
            handler = self._handler_dict.get(apid)
        for tm_packet in tm_queue:
            if handler is not None:
                handler.callback(apid, tm_packet, handler.user_args)
            else:
                LOGGER.warning(f"No valid handler for TM with APID {apid} found")
