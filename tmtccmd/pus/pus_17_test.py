from __future__ import annotations
import enum

from spacepackets.ecss import PusTelecommand, PusServices
from spacepackets.ecss.pus_17_test import Subservices


class CustomSubservices(enum.IntEnum):
    TC_GEN_EVENT = 128


def pack_service_17_ping_command() -> PusTelecommand:
    """Generate a simple ping PUS telecommand packet"""
    return PusTelecommand(service=PusServices.S17_TEST, subservice=Subservices.TC_PING)
