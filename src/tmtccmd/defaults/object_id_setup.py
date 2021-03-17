from typing import Dict
from tmtccmd.core.definitions import CoreObjectIds


def get_core_object_ids() -> Dict[int, bytearray]:
    """
    These are the object IDs for the tmtccmd core. The core will usually take care of
    inserting these into the object manager during the program initialization.
    :return: Dictionary of the core object IDs
    """
    object_id_dict = {
        CoreObjectIds.INVALID: bytearray([0xff, 0xff, 0xff, 0xff]),
    }
    return object_id_dict
