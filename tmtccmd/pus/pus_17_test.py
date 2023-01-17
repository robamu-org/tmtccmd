from __future__ import annotations
import enum

from spacepackets.ecss import PusTelecommand, PusService
from spacepackets.ecss.pus_17_test import Subservice


class CustomSubservice(enum.IntEnum):
    TC_GEN_EVENT = 128


def pack_service_17_ping_command() -> PusTelecommand:
    """Generate a simple ping PUS telecommand packet"""
    return PusTelecommand(service=PusService.S17_TEST, subservice=Subservice.TC_PING)
