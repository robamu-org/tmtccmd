import struct

from spacepackets.ecss import PusTelecommand
from tmtccmd.pus.pus_8_funccmd import Subservices


def make_fsfw_action_cmd(
    object_id: bytes, action_id: int, user_data: bytes = bytes()
) -> PusTelecommand:
    data_to_pack = bytearray(object_id)
    data_to_pack += make_action_id(action_id) + user_data
    return PusTelecommand(
        service=8, subservice=Subservices.FUNCTIONAL_CMD, app_data=data_to_pack
    )


def make_action_id(action_id: int) -> bytearray:
    return bytearray(struct.pack("!I", action_id))
