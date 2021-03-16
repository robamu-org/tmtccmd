from typing import Dict
from tmtccmd.core.definitions import CoreObjectIds

def __get_core_object_ids() -> Dict[int, bytearray]:
    object_id_dict = {
        CoreObjectIds.INVALID: bytearray([0xff, 0xff, 0xff, 0xff]),
    }
    return object_id_dict
