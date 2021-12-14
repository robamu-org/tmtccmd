"""
@brief      Core components for mode commanding (custom PUS service)
"""
import enum
import struct


class Modes(enum.IntEnum):
    OFF = (0,)
    ON = (1,)
    NORMAL = (2,)
    RAW = 3


def pack_mode_data(object_id: bytearray, mode: Modes, submode: int) -> bytearray:
    """Mode 0: Off, Mode 1: Mode On, Mode 2: Mode Normal, Mode 3: Mode Raw"""
    # Normal mode
    mode_packed = struct.pack("!I", mode)
    # Submode default
    submode_byte = struct.pack("B", submode)
    mode_data = object_id + mode_packed + submode_byte
    return mode_data
