from typing import Callable, Dict, Optional, Tuple, List

from tmtccmd.tm.handler import TmHandler
from tmtccmd.tm.definitions import TelemetryQueueT, TmTypes
from tmtccmd.sendreceive.tm_listener import QueueListT
from tmtccmd.utility.tmtc_printer import TmTcPrinter
from tmtccmd.utility.logger import get_console_logger

CcsdsCallbackT = Callable[[int, bytearray, TmTcPrinter], None]

LOGGER = get_console_logger()
HandlerDictT = Dict[int, Tuple[CcsdsCallbackT, int]]


class CcsdsTmHandler(TmHandler):
    """Generic CCSDS handler class. The user can create an instance of this class to handle
    CCSDS packets with different APIDs"""
    def __init__(self, tmtc_printer: Optional[TmTcPrinter] = None):
        super().__init__(tm_type=TmTypes.CCSDS_SPACE_PACKETS)
        self._handler_dict: HandlerDictT = dict()
        self._tmtc_printer = tmtc_printer

    def initialize(self, tmtc_printer: TmTcPrinter):
        self._tmtc_printer = tmtc_printer

    def add_tm_handler(self, apid: int, pus_tm_handler: CcsdsCallbackT, max_queue_len: int):
        """Add a TM handler for a certain APID. The handler is a callback function which
        will be called if telemetry with that APID arrives
        :param apid:            CCSDS Application Process ID
        :param pus_tm_handler:  Callback function
        :param max_queue_len:
        :return:
        """
        self._handler_dict[apid] = pus_tm_handler, max_queue_len

    def get_apid_queue_len_list(self) -> List[Tuple[int, int]]:
        list = []
        for apid, handler_tuple in self._handler_dict.items():
            list.append((apid, handler_tuple[1]))
        return list

    def handle_packet_queues(self, packet_queue_list: QueueListT):
        for queue_tuple in packet_queue_list:
            apid = queue_tuple[0]
            handler_tuple = self._handler_dict.get(apid)
            if handler_tuple is not None:
                ccsds_cb = handler_tuple[0]
                self.handle_ccsds_packet_queue(
                    apid=apid, packet_queue=queue_tuple[1], ccsds_cb=ccsds_cb
                )

    def handle_ccsds_packet_queue(
            self, apid: int, packet_queue: TelemetryQueueT,
            ccsds_cb: Optional[CcsdsCallbackT] = None
    ):
        for tm_packet in packet_queue:
            if ccsds_cb is None:
                ccsds_cb = self._handler_dict[apid][0]
            ccsds_cb(apid, tm_packet, self._tmtc_printer)
