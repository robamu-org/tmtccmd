import enum
from typing import cast
from tmtccmd.ccsds.handler import CcsdsHandler


class TmTypes(enum.Enum):
    CCSDS = enum.auto()


class TmHandler:
    def __init__(self):
        self.handler_dict = dict()

    def add_ccsds_handler(self, apid: int, handler_object: CcsdsHandler):
        self.handler_dict[apid] = handler_object

    def handle_ccsds_packet(self, apid: int, packet: bytearray):
        handler = self.handler_dict.get(apid)
        if handler is not None:
            handler = cast(CcsdsHandler, handler)
            handler.handle_ccsds_packet(packet)
