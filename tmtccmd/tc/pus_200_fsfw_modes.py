"""
@brief      Core components for mode commanding (custom PUS service)
"""
import enum
import struct
from typing import Union

from spacepackets.ecss import PusTelecommand
from tmtccmd.pus import CustomPusServices
from tmtccmd.pus.pus_200_fsfw_mode import Subservices


class Modes(enum.IntEnum):
    OFF = 0
    ON = 1
    NORMAL = 2
    RAW = 3


def pack_mode_data(
    object_id: bytes, mode: Union[Modes, int], submode: int
) -> bytearray:
    """FSFW modes: Mode 0: Off, Mode 1: Mode On, Mode 2: Mode Normal, Mode 3: Mode Raw"""
    mode_data = bytearray()
    mode_data += object_id + struct.pack("!I", mode) + struct.pack("B", submode)
    return mode_data


def pack_mode_command(
    object_id: bytes, mode: Union[int, Modes], submode: int
) -> PusTelecommand:
    return PusTelecommand(
        service=CustomPusServices.SERVICE_200_MODE,
        subservice=Subservices.TC_MODE_COMMAND,
        app_data=pack_mode_data(object_id, mode, submode),
    )
