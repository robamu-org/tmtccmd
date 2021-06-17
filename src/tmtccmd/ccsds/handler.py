from typing import Callable
from abc import abstractmethod
from tmtccmd.utility.logger import get_logger

CcsdsCallbackT = Callable[[int, bytearray], None]

LOGGER = get_logger()


class CcsdsHandler:
    def __init__(self, apid: int):
        self.apid = apid

    @abstractmethod
    def handle_ccsds_packet(self, packet: bytearray) -> any:
        pass
