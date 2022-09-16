from __future__ import annotations

from typing import Union, Dict, Optional

from spacepackets.util import UnsignedByteField


class ObjectIdBase(UnsignedByteField):
    """Base class for unsigned object IDs with different byte sizes"""

    def __init__(self, obj_id: int, byte_len: int, name: Optional[str] = None):
        super().__init__(val=obj_id, byte_len=byte_len)
        if name is None:
            self.name = "Unknown"
        else:
            self.name = name

    def __str__(self):
        return f"Object ID {self.name} with ID {self.as_hex_string}"

    @property
    def as_hex_string(self) -> str:
        if self.byte_len == 1:
            return f"{self.obj_id:#04x}"
        elif self.byte_len == 2:
            return f"{self.obj_id:#06x}"
        elif self.byte_len == 4:
            return f"{self.obj_id:#010x}"
        elif self.byte_len == 8:
            return f"{self.obj_id:#018x}"

    @property
    def obj_id(self) -> int:
        return int(self)

    @obj_id.setter
    def obj_id(self, obj_id: Union[int, bytes]):
        """This setter function takes a raw byte stream to deserialize an object ID, or the ID
        as an integer.

        :raise ValueError: Invalid ID
        """
        self.value = obj_id


class ObjectIdU32(ObjectIdBase):
    """A helper object for a unique object identifier which has a raw unsigned
    32-bit representation.

    >>> obj_id = ObjectIdU32(42, "Object with the answer to everything")
    >>> int(obj_id)
    42
    >>> obj_id.name
    'Object with the answer to everything'
    >>> obj_id.as_bytes.hex(sep=",")
    '00,00,00,2a'
    >>> obj_id.as_hex_string
    '0x0000002a'
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
