"""
@brief      Core components for mode commanding (custom PUS service)
"""
import struct


def pack_mode_data(object_id: bytearray, mode_: int, submode_: int) -> bytearray:
    """
    Mode 0: Off, Mode 1: Mode On, Mode 2: Mode Normal, Mode 3: Mode Raw
    """
    # Normal mode
    mode = struct.pack(">I", mode_)
    # Submode default
    submode = struct.pack('B', submode_)
    mode_data = object_id + mode + submode
    return mode_data
