from __future__ import annotations
import struct
from tmtccmd.utility.logger import get_console_logger

LOGGER = get_console_logger()


class ObjectId:
    def __init__(self, object_id: int):
        self.object_id = object_id
        self.id_as_bytes = bytearray()
        self.set(object_id=object_id)

    def set(self, object_id: int):
        self.object_id = object_id
        self.id_as_bytes = struct.pack('!I', self.object_id)

    def set_from_bytes(self, obj_id_as_bytes: bytearray):
        if len(obj_id_as_bytes) != 4:
            LOGGER.warning(f'Invalid object ID length {len(obj_id_as_bytes)}')
            raise ValueError
        self.id_as_bytes = obj_id_as_bytes
        self.object_id = struct.unpack('!I', self.id_as_bytes[:])[0]

    @classmethod
    def from_bytes(cls, obj_id_as_bytes: bytearray) -> ObjectId:
        obj_id = ObjectId(object_id=0)
        obj_id.set_from_bytes(obj_id_as_bytes=obj_id_as_bytes)
        return obj_id

    def get_id(self) -> int:
        return self.object_id

    def as_bytes(self) -> bytes:
        return self.id_as_bytes

    def as_string(self) -> str:
        return f'0x{self.object_id:08x}'
