from typing import Dict

from tmtccmd.utility.logger import get_console_logger

LOGGER = get_console_logger()
__OBJECT_ID_DICT = dict()


def insert_object_id(object_id: bytes, object_id_info: list):
    __OBJECT_ID_DICT[object_id] = object_id_info


def insert_object_ids(object_id_dict: Dict[bytes, list]):
    if object_id_dict is not None:
        __OBJECT_ID_DICT.update(object_id_dict)


def get_object_id_info(object_id: bytes):
    return __OBJECT_ID_DICT.get(object_id)
