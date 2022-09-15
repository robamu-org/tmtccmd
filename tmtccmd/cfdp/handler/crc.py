from pathlib import Path
from typing import Optional

from crcmod.predefined import PredefinedCrc

from spacepackets.cfdp import ChecksumType, NULL_CHECKSUM_U32
from tmtccmd.cfdp.filestore import VirtualFilestore
from tmtccmd.cfdp.handler.defs import ChecksumNotImplemented, SourceFileDoesNotExist


class Crc32Helper:
    def __init__(self, init_type: ChecksumType, vfs: VirtualFilestore):
        self.checksum_type = init_type
        self.vfs = vfs

    def _verify_checksum(self):
        if self.checksum_type not in [
            ChecksumType.NULL_CHECKSUM,
            ChecksumType.CRC_32,
            ChecksumType.CRC_32C,
        ]:
            raise ChecksumNotImplemented(self.checksum_type)

    def checksum_type_to_crcmod_str(self) -> Optional[str]:
        if self.checksum_type == ChecksumType.NULL_CHECKSUM:
            return None
        if self.checksum_type == ChecksumType.CRC_32:
            return "crc32"
        elif self.checksum_type == ChecksumType.CRC_32C:
            return "crc32c"

    def generate_crc_calculator(self) -> PredefinedCrc:
        self._verify_checksum()
        return PredefinedCrc(self.checksum_type_to_crcmod_str())

    def calc_for_file(self, file: Path, file_sz: int, segment_len: int) -> bytes:
        if self.checksum_type == ChecksumType.NULL_CHECKSUM:
            return NULL_CHECKSUM_U32
        crc_obj = self.generate_crc_calculator()
        if segment_len == 0:
            raise ValueError("Segment length can not be 0")
        if not file.exists():
            raise SourceFileDoesNotExist(file)
        current_offset = 0
        # Calculate the file CRC
        with open(file, "rb") as of:
            while current_offset < file_sz:
                if current_offset + segment_len > file_sz:
                    read_len = file_sz - current_offset
                else:
                    read_len = segment_len
                if read_len > 0:
                    crc_obj.update(
                        self.vfs.read_from_opened_file(of, current_offset, read_len)
                    )
                current_offset += read_len
            return crc_obj.digest()
