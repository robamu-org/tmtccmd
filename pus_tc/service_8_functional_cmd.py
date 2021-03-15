import enum
import struct

from tmtccmd.pus_tc.base import PusTelecommand


class Srv8Subservices(enum.IntEnum):
    FUNC_CMD = 128,
    DATA_REPLY = 130


def generate_action_command(object_id: bytearray, action_id: int, data: bytearray = bytearray([]),
                            ssc: int = 0) -> PusTelecommand:
    data_to_pack = bytearray(object_id)
    data_to_pack += make_action_id(action_id) + data
    return PusTelecommand(
        service=8, subservice=Srv8Subservices.FUNC_CMD, ssc=ssc, app_data=data_to_pack
    )


def make_action_id(action_id: int) -> bytearray:
    return bytearray(struct.pack('!I', action_id))
