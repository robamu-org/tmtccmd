import struct

import deprecation

from spacepackets.ecss import PusTelecommand
from tmtccmd.pus.s8_fsfw_funccmd_defs import CustomSubservice
from tmtccmd.version import get_version


@deprecation.deprecated(
    deprecated_in="v4.0.0a2",
    current_version=get_version(),
    details="use create... API instead",
)
def make_fsfw_action_cmd(
    object_id: bytes,
    action_id: int,
    user_data: bytes = bytes(),
    apid: int = 0,
    seq_count: int = 0,
) -> PusTelecommand:
    return create_action_cmd(
        object_id=object_id,
        action_id=action_id,
        user_data=user_data,
        apid=apid,
        seq_count=seq_count,
    )


def create_action_cmd(
    object_id: bytes,
    action_id: int,
    user_data: bytes = bytes(),
    apid: int = 0,
    seq_count: int = 0,
) -> PusTelecommand:
    data_to_pack = bytearray(object_id)
    data_to_pack += make_action_id(action_id) + user_data
    return PusTelecommand(
        service=8,
        subservice=CustomSubservice.TC_FUNCTIONAL_CMD,
        app_data=data_to_pack,
        apid=apid,
        seq_count=seq_count,
    )


def make_action_id(action_id: int) -> bytearray:
    return bytearray(struct.pack("!I", action_id))
