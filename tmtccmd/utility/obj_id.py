from __future__ import annotations
from typing import Union, Dict, Optional
import struct
from tmtccmd.logging import get_console_logger

LOGGER = get_console_logger()


class ObjectIdU32:
    """A helper object for a unique object identifier which has a raw unsigned 32-bit representation"""

    def __init__(self, object_id: int, name: Optional[str] = None):
        self._id_as_bytes = bytes()
        self.id = object_id
        if name is None:
            self.name = "Unknown"
        else:
            self.name = name

    def __str__(self):
        return f"32-bit Object ID {self.name} with ID {self.as_hex_string}"

    def __repr__(self):
        return f"{self.__class__.__name__}(object_id={self.id!r}, name={self.name!r})"

    def __hash__(self):
        self.id.__hash__()

    def __eq__(self, other: ObjectIdU32):
        return self.id == other.id

    @classmethod
    def from_bytes(cls, obj_id_as_bytes: bytes) -> ObjectIdU32:
        obj_id = ObjectIdU32(object_id=0)
        obj_id.id = obj_id_as_bytes
        return obj_id

    @property
    def id(self) -> int:
        return self._object_id

    @id.setter
    def id(self, new_id: Union[int, bytes]):
        if isinstance(new_id, int):
            self._object_id = new_id
            self._id_as_bytes = struct.pack("!I", self._object_id)
        elif isinstance(new_id, bytes) or isinstance(new_id, bytearray):
            if len(new_id) != 4:
                raise ValueError(f"Invalid object ID length {len(new_id)}")
            self._id_as_bytes = bytes(new_id)
            self._object_id = struct.unpack("!I", self._id_as_bytes[:])[0]
        else:
            raise TypeError("Is not integer of bytes type")

    @property
    def as_int(self) -> int:
        return self._object_id

    @property
    def as_bytes(self) -> bytes:
        return self._id_as_bytes

    @property
    def as_hex_string(self) -> str:
        return f"{self._object_id:#010x}"


ObjectIdDictT = Dict[bytes, ObjectIdU32]
