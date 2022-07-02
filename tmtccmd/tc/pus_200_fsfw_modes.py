"""
@brief      Core components for mode commanding (custom PUS service)
"""
import enum
import struct
from tmtccmd.pus.pus_200_fsfw_mode import Subservices


class Modes(enum.IntEnum):
    OFF = 0
    ON = 1
    NORMAL = 2
    RAW = 3


def pack_mode_data(object_id: bytes, mode: Modes, submode: int) -> bytearray:
    """Mode 0: Off, Mode 1: Mode On, Mode 2: Mode Normal, Mode 3: Mode Raw"""
    mode_data = bytearray()
    mode_data += object_id + struct.pack("!I", mode) + struct.pack("B", submode)
    return mode_data
