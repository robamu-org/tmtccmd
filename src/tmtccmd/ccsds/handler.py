from typing import Callable
from abc import abstractmethod
from tmtccmd.config.definitions import TmHandler, TmTypes
from tmtccmd.utility.logger import get_logger

CcsdsCallbackT = Callable[[int, bytearray], None]

LOGGER = get_logger()


class CcsdsTmHandler(TmHandler):
    def __init__(self, apid: int):
        super().__init__(tm_type=TmTypes.CCSDS_SPACE_PACKETS)
        self._apid = apid

    def get_apid(self):
        return self._apid

    @abstractmethod
    def handle_ccsds_packet(self, packet: bytearray) -> any:
        pass
