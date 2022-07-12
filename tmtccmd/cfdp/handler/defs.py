from dataclasses import dataclass
from pathlib import Path

from spacepackets.cfdp import Direction, ChecksumTypes
from spacepackets.util import UnsignedByteField


class NoRemoteEntityCfgFound(Exception):
    def __init__(self, entity_id: UnsignedByteField, *args, **kwargs):
        super().__init__(args, kwargs)
        self.remote_entity_id = entity_id


class SourceFileDoesNotExist(Exception):
    def __init__(self, file: Path, *args, **kwargs):
        super().__init__(args, kwargs)
        self.file = file


class ChecksumNotImplemented(Exception):
    def __init__(self, checksum_type: ChecksumTypes, *args, **kwargs):
        super().__init__(args, kwargs)
        self.checksum_type = checksum_type


class PacketSendNotConfirmed(Exception):
    pass


class InvalidPduDirection(Exception):
    def __init__(self, expected_dir: Direction, found_dir: Direction, *args, **kwargs):
        super().__init__(args, kwargs)
        self.expected_dir = expected_dir
        self.found_dir = found_dir


class InvalidSourceId(Exception):
    """Invalid source entity ID. This is not necessarily the sender of a packet but actually the
    entity that started a transaction, or the entity which is transferring a file"""

    def __init__(
        self,
        expected_src_id: UnsignedByteField,
        found_src_id: UnsignedByteField,
        *args,
        **kwargs
    ):
        super().__init__(args, kwargs)
        self.expected_src_id = expected_src_id
        self.found_src_id = found_src_id


class InvalidDestinationId(Exception):
    """Invalid destination entity ID. This is not necessarily the receiver of a packet but actually
    the recipient of a file, or the entity receiving file data and metadata PDUs"""

    def __init__(
        self,
        expected_dest_id: UnsignedByteField,
        found_dest_id: UnsignedByteField,
        *args,
        **kwargs
    ):
        super().__init__(args, kwargs)
        self.expected_dest_id = expected_dest_id
        self.found_dest_id = found_dest_id


class BusyError(Exception):
    pass


@dataclass
class FileParams:
    offset: int = 0
    segment_len: int = 0
    crc32: bytes = bytes()
    size: int = 0

    def reset(self):
        self.offset = 0
        self.segment_len = 0
        self.crc32 = bytes()
        self.size = 0
