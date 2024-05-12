from tmtccmd.util.obj_id import ComponentIdMapping, ObjectIdU32


INVALID_ID = bytes([0xFF, 0xFF, 0xFF, 0xFF])


def get_base_component_id_mapping() -> ComponentIdMapping:
    """These are the object IDs for the tmtccmd core. The core will usually take care of
    inserting these into the object manager during the program initialization.

    :return Dictionary of the core object IDs
    """
    invalid_id = ObjectIdU32.from_bytes(raw=INVALID_ID)
    invalid_id.name = "Invalid ID"
    object_id_dict = {INVALID_ID: invalid_id}
    return object_id_dict


def get_core_object_ids() -> ComponentIdMapping:
    return get_base_component_id_mapping()
