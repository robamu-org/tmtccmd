from typing import Tuple

from tmtccmd.utility.tmtcc_logger import get_logger

LOGGER = get_logger()


def get_sp_packet_id_bytes(
        version: int, packet_type: int, data_field_header_flag: int, apid: int
) -> Tuple[int, int]:
    byte_one = \
        ((version << 5) & 0xE0) | ((packet_type & 0x01) << 4) | \
        ((data_field_header_flag & 0x01) << 3) | ((apid & 0x700) >> 8)
    byte_two = apid & 0xFF
    return byte_one, byte_two


def get_sp_packet_sequence_control(sequence_flags: int, source_sequence_count: int) -> int:
    if sequence_flags > 3:
        LOGGER.warning("Sequence flag value larger than 0b11! Setting to 0b11..")
        sequence_flags = 3
    if source_sequence_count > 0x3fff:
        LOGGER.warning("Source sequence count largen than 0x3fff. Larger bits are cut off!")
    return (source_sequence_count & 0x3FFF) | (sequence_flags << 14)


def get_sp_space_packet_header(
        packet_id_byte_one: int, packet_id_byte_two: int, packet_sequence_control: int,
        data_length: int
) -> bytearray:
    header = bytearray()
    header.append(packet_id_byte_one)
    header.append(packet_id_byte_two)
    header.append((packet_sequence_control & 0xFF00) >> 8)
    header.append(packet_sequence_control & 0xFF)
    header.append((data_length & 0xFF00) >> 8)
    header.append(data_length & 0xFF)
    return header
