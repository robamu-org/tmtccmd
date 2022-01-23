from __future__ import annotations
from typing import Union
import struct
from tmtccmd.utility.logger import get_console_logger

LOGGER = get_console_logger()


class ObjectId:
    def __init__(self, object_id: int):
        self.id = object_id

    @classmethod
    def from_bytes(cls, obj_id_as_bytes: bytearray) -> ObjectId:
        obj_id = ObjectId(object_id=0)
        obj_id.id = obj_id_as_bytes
        return obj_id

    @property
    def id(self) -> int:
        return self._object_id

    @id.setter
    def id(self, new_id: Union[int, bytearray]):
        if isinstance(new_id, int):
            self._object_id = new_id
            self._id_as_bytes = struct.pack("!I", self._object_id)
        elif isinstance(new_id, bytearray):
            if len(new_id) != 4:
                LOGGER.warning(f"Invalid object ID length {len(new_id)}")
                raise ValueError
            self._id_as_bytes = new_id
            self._object_id = struct.unpack("!I", self._id_as_bytes[:])[0]
        else:
            raise ValueError

    @property
    def as_int(self) -> int:
        return self._object_id

    @property
    def as_bytes(self) -> bytes:
        return self._id_as_bytes

    @property
    def as_string(self) -> str:
        return f"0x{self._object_id:08x}"
