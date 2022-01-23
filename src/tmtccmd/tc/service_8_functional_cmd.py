import enum
import struct

from tmtccmd.tc.definitions import PusTelecommand
from spacepackets.ecss.conf import get_default_tc_apid


class Srv8Subservices(enum.IntEnum):
    FUNC_CMD = (128,)
    DATA_REPLY = 130


def generate_action_command(
    object_id: bytes,
    action_id: int,
    app_data: bytes = bytes(),
    ssc: int = 0,
    apid: int = -1,
) -> PusTelecommand:
    if apid == -1:
        apid = get_default_tc_apid()
    data_to_pack = bytearray(object_id)
    data_to_pack += make_action_id(action_id) + app_data
    return PusTelecommand(
        service=8,
        subservice=Srv8Subservices.FUNC_CMD,
        ssc=ssc,
        app_data=data_to_pack,
        apid=apid,
    )


def make_action_id(action_id: int) -> bytearray:
    return bytearray(struct.pack("!I", action_id))
