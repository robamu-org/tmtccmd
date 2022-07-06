from __future__ import annotations

from abc import ABC
from typing import Union, Dict, Optional
import struct

from spacepackets.ecss.fields import byte_num_to_unsigned_struct_specifier
from tmtccmd.logging import get_console_logger

LOGGER = get_console_logger()


class ObjectIdBase(ABC):
    """Base class for unsigned object IDs with different byte sizes"""

    def __init__(self, obj_id: int, byte_width: int, name: Optional[str] = None):
        self._id_as_bytes = bytes()
        if byte_width not in [1, 2, 4, 8]:
            raise ValueError("Only byte widths 1, 2, 4 and 8 are allowed for Object ID")
        self._byte_width = byte_width
        self._id = 0
        self.obj_id = obj_id
        if name is None:
            self.name = "Unknown"
        else:
            self.name = name

    def __str__(self):
        return f"Object ID {self.name} with ID {self.as_hex_string}"

    @property
    def byte_width(self):
        return self._byte_width

    @property
    def as_hex_string(self) -> str:
        if self.byte_width == 1:
            return f"{self.obj_id:#04x}"
        elif self.byte_width == 2:
            return f"{self.obj_id:#06x}"
        elif self.byte_width == 4:
            return f"{self.obj_id:#010x}"
        elif self.byte_width == 8:
            return f"{self.obj_id:#018x}"

    @property
    def obj_id(self):
        return self._id

    @obj_id.setter
    def obj_id(self, obj_id: Union[int, bytes]):
        """This setter function takes a raw byte stream to deserialize an object ID, or the ID
        as an integer.

        :raise ValueError: Invalid ID
        """
        if isinstance(obj_id, int):
            if not self._verify_id(obj_id):
                raise ValueError(
                    f"Invalid Object ID {obj_id}, not unsigned or too large"
                )
            self._id = obj_id
            self._id_as_bytes = struct.pack(
                byte_num_to_unsigned_struct_specifier(self.byte_width), self._id
            )
        elif isinstance(obj_id, bytes) or isinstance(obj_id, bytearray):
            if len(obj_id) < self.byte_width:
                raise ValueError(
                    f"Supplied bytes not large enough for object ID of width {self.byte_width}"
                )
            self._id_as_bytes = bytes(obj_id[0 : self.byte_width])
            self._id = struct.unpack(
                byte_num_to_unsigned_struct_specifier(self.byte_width),
                self._id_as_bytes,
            )[0]
        else:
            raise TypeError("Is not integer of bytes type")

    def _verify_id(self, obj_id: int) -> bool:
        if obj_id < 0:
            return False
        if self.byte_width == 1 and obj_id > pow(2, 8) - 1:
            return False
        elif self.byte_width == 2 and obj_id > pow(2, 16) - 1:
            return False
        elif self.byte_width == 4 and obj_id > pow(2, 32) - 1:
            return False
        return True

    @property
    def as_int(self) -> int:
        return self.obj_id

    @property
    def as_bytes(self) -> bytes:
        return self._id_as_bytes

    def __hash__(self):
        return hash((self._id, self.byte_width))

    def __eq__(self, other: ObjectIdBase):
        return self.obj_id == other.obj_id and self.byte_width == other.byte_width


class ObjectIdU32(ObjectIdBase):
    """A helper object for a unique object identifier which has a raw unsigned
    32-bit representation.
    """

    def __init__(self, obj_id: int, name: Optional[str] = None):
        super().__init__(obj_id, 4, name)

    def __repr__(self):
        return (
            f"{self.__class__.__name__}(object_id={self.obj_id!r}, name={self.name!r})"
        )

    @classmethod
    def from_bytes(cls, obj_id_as_bytes: bytes) -> ObjectIdU32:
        obj_id = ObjectIdU32(obj_id=0)
        obj_id.obj_id = obj_id_as_bytes
        return obj_id


class ObjectIdU16(ObjectIdBase):
    """A helper object for a unique object identifier which has a raw unsigned
    16-bit representation.
    """

    def __init__(self, obj_id: int, name: Optional[str] = None):
        super().__init__(obj_id, 2, name)

    def __repr__(self):
        return (
            f"{self.__class__.__name__}(object_id={self.obj_id!r}, name={self.name!r})"
        )

    @classmethod
    def from_bytes(cls, obj_id_as_bytes: bytes) -> ObjectIdU16:
        obj_id = ObjectIdU16(obj_id=0)
        obj_id.obj_id = obj_id_as_bytes
        return obj_id


class ObjectIdU8(ObjectIdBase):
    """A helper object for a unique object identifier which has a raw unsigned
    8-bit representation.
    """

    def __init__(self, obj_id: int, name: Optional[str] = None):
        super().__init__(obj_id, 1, name)

    def __repr__(self):
        return (
            f"{self.__class__.__name__}(object_id={self.obj_id!r}, name={self.name!r})"
        )

    @classmethod
    def from_bytes(cls, obj_id_as_bytes: bytes) -> ObjectIdU8:
        obj_id = ObjectIdU8(obj_id=0)
        obj_id.obj_id = obj_id_as_bytes
        return obj_id


ObjectIdDictT = Dict[bytes, ObjectIdBase]
