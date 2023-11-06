from dataclasses import dataclass
from typing import Optional


@dataclass
class _FileParamsBase:
    progress: int
    segment_len: int
    crc32: Optional[bytes]
    no_file_data: bool
    file_size: int

    @classmethod
    def empty(cls):
        return cls(
            progress=0,
            segment_len=0,
            crc32=None,
            file_size=0,
            no_file_data=False,
        )

    def reset(self):
        self.progress = 0
        self.segment_len = 0
        self.crc32 = bytes()
        self.file_size = 0
