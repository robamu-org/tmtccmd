import struct
from unittest import TestCase
from tmtccmd.cfdp.handler.crc import CrcHelper, calc_modular_checksum
from tmtccmd.cfdp.user import HostFilestore
from spacepackets.cfdp import ChecksumType


EXAMPLE_DATA_CFDP = bytes(
    [
        0x00,
        0x01,
        0x02,
        0x03,
        0x04,
        0x05,
        0x06,
        0x07,
        0x08,
        0x09,
        0x0A,
        0x0B,
        0x0C,
        0x0D,
        0x0E,
    ]
)


class TestChecksumHelper(TestCase):
    def setUp(self):
        self.crc_helper = CrcHelper(ChecksumType.NULL_CHECKSUM, HostFilestore())
        self.file_path = "/tmp/crc_file"
        with open(self.file_path, "wb") as file:
            file.write(EXAMPLE_DATA_CFDP)
        segments_to_add = []
        for i in range(4):
            if (i + 1) * 4 > len(EXAMPLE_DATA_CFDP):
                data_to_add = EXAMPLE_DATA_CFDP[i * 4 :].ljust(4, bytes([0]))
            else:
                data_to_add = EXAMPLE_DATA_CFDP[i * 4 : (i + 1) * 4]
            segments_to_add.append(
                int.from_bytes(
                    data_to_add,
                    byteorder="big",
                    signed=False,
                )
            )
        full_sum = sum(segments_to_add)
        print(full_sum)
        full_sum %= 2**32

        self.expected_checksum_for_example = struct.pack("!I", full_sum)

    def test_modular_checksum(self):
        self.assertEqual(
            calc_modular_checksum(self.file_path), self.expected_checksum_for_example
        )