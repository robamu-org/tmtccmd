from typing import Dict


def set_core_object_ids(object_id_dict: Dict[int, bytearray]):
    from tmtccmd.core.definitions import CoreObjectIds
    object_id_dict.update({
        CoreObjectIds.INVALID: bytearray([0xff, 0xff, 0xff, 0xff]),
    })
