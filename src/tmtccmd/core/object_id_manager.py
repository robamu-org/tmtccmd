import struct
import sys
from typing import Dict

from tmtccmd.utility.tmtcc_logger import get_logger
from tmtccmd.core.definitions import CoreObjectIds

LOGGER = get_logger()


class ObjectIdManager:
    """
    Global object manager. This is a singleton class, only one global instance should be created.
    The instance can be retrieved with the get_manager class method.
    """
    MANAGER_INSTANCE = None

    @classmethod
    def get_manager(cls):
        """
        Retrieve a handle to the global object ID manager.
        """
        if cls.MANAGER_INSTANCE is None:
            cls.MANAGER_INSTANCE = ObjectIdManager()
        return cls.MANAGER_INSTANCE

    def __init__(self):
        self.object_id_dict = dict()

    # noinspection PyUnresolvedReferences
    def get_object_id(self, object_id_key: int):
        object_id = self.object_id_dict.get(object_id_key)
        if object_id is None:
            try:
                LOGGER.error("This key does not exist in the object ID dictionary!")
            except ImportError:
                print("Could not import LOGGER!")
            return bytearray(4)
        else:
            return object_id

    def get_key_from_raw_object_id(self, object_id: bytearray):
        for key, raw_id in self.object_id_dict.items():
            if raw_id == object_id:
                return key
        return None

    def insert_object_id(self, object_id_key: int, object_id: bytearray):
        self.object_id_dict.update({object_id_key: object_id})

    def insert_object_ids(self, object_id_dict: Dict[int, bytearray]):
        self.object_id_dict.update(object_id_dict)


def insert_object_id(object_id_key: int, object_id: bytearray):
    return ObjectIdManager.get_manager().insert_object_id(
        object_id_key=object_id_key, object_id=object_id
    )


def insert_object_ids(object_id_dict: Dict[int, bytearray]):
    return ObjectIdManager.get_manager().insert_object_ids(object_id_dict=object_id_dict)


def get_object_id(object_id_key: int):
    return ObjectIdManager.get_manager().get_object_id(object_id_key)


def get_key_from_raw_object_id(object_id_raw: bytearray) -> int:
    if not isinstance(object_id_raw, bytearray):
        LOGGER.warning("Invalid object ID type.")
        return CoreObjectIds.INVALID
    if len(object_id_raw) != 4:
        LOGGER.warning("Invalid object ID length")
        return CoreObjectIds.INVALID
    return ObjectIdManager.get_manager().get_key_from_raw_object_id(object_id_raw)


def get_key_from_int_object_id(object_id_int: int) -> int:
    if not isinstance(object_id_int, int):
        LOGGER.warning("Invalid object ID type.")
        return CoreObjectIds.INVALID
    object_id_raw = bytearray(struct.pack("!I", object_id_int))
    return ObjectIdManager.get_manager().get_key_from_raw_object_id(object_id_raw)
