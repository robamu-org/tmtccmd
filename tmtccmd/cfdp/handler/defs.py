from dataclasses import dataclass
from pathlib import Path

from spacepackets.cfdp import Direction, ChecksumTypes
from spacepackets.util import UnsignedByteField


class NoRemoteEntityCfgFound(Exception):
    def __init__(self, entity_id: UnsignedByteField, *args, **kwargs):
        super().__init__(args, kwargs)
        self.remote_entity_id = entity_id

    def __str__(self):
        return f"No remote entity found for entity ID {self.remote_entity_id}"


class SourceFileDoesNotExist(Exception):
    def __init__(self, file: Path, *args, **kwargs):
        super().__init__(args, kwargs)
        self.file = file

    def __str__(self):
        return f"Source file {self.file} does not exist"


class ChecksumNotImplemented(Exception):
    def __init__(self, checksum_type: ChecksumTypes, *args, **kwargs):
        super().__init__(args, kwargs)
        self.checksum_type = checksum_type

    def __str__(self):
        return f"{self.checksum_type} not implemented"


class PacketSendNotConfirmed(Exception):
    pass


class InvalidPduDirection(Exception):
    def __init__(self, expected_dir: Direction, found_dir: Direction, *args, **kwargs):
        super().__init__(args, kwargs)
        self.expected_dir = expected_dir
        self.found_dir = found_dir

    def __str__(self):
        return f"Expected direction {self.expected_dir}, got {self.found_dir}"


class InvalidSourceId(Exception):
    """Invalid source entity ID. This is not necessarily the sender of a packet but actually the
    entity that started a transaction, or the entity which is transferring a file"""

    def __init__(
        self,
        expected_src_id: UnsignedByteField,
        found_src_id: UnsignedByteField,
        *args,
        **kwargs,
    ):
        super().__init__(args, kwargs)
        self.expected_src_id = expected_src_id
        self.found_src_id = found_src_id

    def __str__(self):
        return f"Expected source {self.expected_src_id}, got {self.found_src_id}"


class InvalidDestinationId(Exception):
    """Invalid destination entity ID. This is not necessarily the receiver of a packet but actually
    the recipient of a file, or the entity receiving file data and metadata PDUs"""

    def __init__(
        self,
        expected_dest_id: UnsignedByteField,
        found_dest_id: UnsignedByteField,
        *args,
        **kwargs,
    ):
        super().__init__(args, kwargs)
        self.expected_dest_id = expected_dest_id
        self.found_dest_id = found_dest_id

    def __str__(self):
        return f"Expected destination {self.expected_dest_id}, got {self.found_dest_id}"


class BusyError(Exception):
    pass


@dataclass
class FileParamsBase:
    offset: int
    segment_len: int
    crc32: bytes
    size: int

    @classmethod
    def empty(cls):
        return cls(offset=0, segment_len=0, crc32=bytes(), size=0)

    def reset(self):
        self.offset = 0
        self.segment_len = 0
        self.crc32 = bytes()
        self.size = 0
