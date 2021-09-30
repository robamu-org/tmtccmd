from __future__ import annotations
import enum
import struct

from tmtccmd.utility.logger import get_console_logger
from tmtccmd.cfdp.definitions import LenInBytes
from tmtccmd.cfdp.conf import get_default_pdu_crc_mode, get_default_source_entity_id, \
    get_default_dest_entity_id


LOGGER = get_console_logger()


class PduType(enum.IntEnum):
    FILE_DIRECTIVE = 0
    FILE_DATA = 1


class Direction(enum.IntEnum):
    TOWARDS_SENDER = 0
    TOWARDS_RECEIVER = 1


class TransmissionModes(enum.IntEnum):
    ACKNOWLEDGED = 0
    UNACKNOWLEDGED = 1


class CrcFlag(enum.IntEnum):
    WITH_CRC = 0
    NO_CRC = 1
    GLOBAL_CONFIG = 2


class SegmentMetadataFlag(enum.IntEnum):
    """Aways 0 and ignored for File Directive PDUs (CCSDS 727.0-B-5 p.75)"""
    NOT_PRESENT = 0
    PRESENT = 1


class SegmentationControl(enum.IntEnum):
    """Always 0 and ignored for File Directive PDUs (CCSDS 727.0-B-5 p.75)"""
    NO_RECORD_BOUNDARIES_PRESERVATION = 0
    RECORD_BOUNDARIES_PRESERVATION = 1


def get_transaction_seq_num_as_bytes(
        transaction_seq_num: int, byte_length: LenInBytes
) -> bytearray:
    """Return the byte representation of the transaction sequece number
    :param transaction_seq_num:
    :param byte_length:
    :raises ValueError: Invalid input
    :return:
    """
    if byte_length == LenInBytes.ONE_BYTE and transaction_seq_num < 255:
        return bytearray([transaction_seq_num])
    if byte_length == LenInBytes.TWO_BYTES and transaction_seq_num < pow(2, 16) - 1:
        return bytearray(struct.pack('!H', transaction_seq_num))
    if byte_length == LenInBytes.FOUR_BYTES and transaction_seq_num < pow(2, 32) - 1:
        return bytearray(struct.pack('!I', transaction_seq_num))
    if byte_length == LenInBytes.EIGHT_BYTES and transaction_seq_num < pow(2, 64) - 1:
        return bytearray(struct.pack('!Q', transaction_seq_num))
    raise ValueError


class PduHeader:
    """This class encapsulates the fixed-format PDU header.
    For more, information, refer to CCSDS 727.0-B-5 p.75"""
    VERSION_BITS = 0b0010_0000
    FIXED_LENGTH = 4

    def __init__(
            self,
            pdu_type: PduType,
            trans_mode: TransmissionModes,
            segment_metadata_flag: SegmentMetadataFlag,
            transaction_seq_num: bytes,
            direction: Direction = Direction.TOWARDS_RECEIVER,
            source_entity_id: bytes = bytes(),
            dest_entity_id: bytes = bytes(),
            crc_flag: CrcFlag = CrcFlag.GLOBAL_CONFIG,
            seg_ctrl: SegmentationControl = SegmentationControl.NO_RECORD_BOUNDARIES_PRESERVATION,
    ):
        """Constructor for PDU header

        :param pdu_type:
        :param direction:
        :param trans_mode:
        :param segment_metadata_flag:
        :param transaction_seq_num:
        :param source_entity_id: If an empty bytearray is passed, the configured default value
        in the CFDP conf module will be used
        :param dest_entity_id: If an empty bytearray is passed, the configured default value
        in the CFDP conf module will be used
        :param crc_flag: If not supplied, assign the default configuration
        :param seg_ctrl:
        :raise ValueError: If some field are invalid or default values were unset
        """
        self.pdu_type = pdu_type
        self.direction = direction
        self.trans_mode = trans_mode
        self.large_file = False
        self.pdu_data_field_length = 0
        self.segmentation_control = seg_ctrl

        self.len_entity_id = 0
        if source_entity_id == bytes():
            source_entity_id = get_default_source_entity_id()
            if source_entity_id == bytes():
                LOGGER.warning(
                    'Can not set default value for source entity ID '
                    'because it has not been set yet'
                )
                raise ValueError
        if dest_entity_id == bytes():
            dest_entity_id = get_default_dest_entity_id()
            if dest_entity_id == bytes():
                LOGGER.warning(
                    'Can not set default value for destination entity ID '
                    'because it has not been set yet'
                )
                raise ValueError
        if source_entity_id is not None and dest_entity_id is not None:
            try:
                self.len_entity_id = self.check_len_in_bytes(len(source_entity_id))
                dest_id_check = self.check_len_in_bytes(len(dest_entity_id))
            except ValueError:
                LOGGER.warning('Invalid length of entity IDs passed')
                raise ValueError
            if dest_id_check != self.len_entity_id:
                LOGGER.warning('Length of destination ID and source ID are not the same')
                raise ValueError

        self.len_transaction_seq_num = 0
        if transaction_seq_num is not None:
            try:
                self.len_transaction_seq_num = self.check_len_in_bytes(len(transaction_seq_num))
            except ValueError:
                LOGGER.warning('Invalid length of transaction sequence number passed')
                raise ValueError
        if crc_flag == CrcFlag.GLOBAL_CONFIG:
            self.crc_flag = get_default_pdu_crc_mode()
        else:
            self.crc_flag = crc_flag
        self.segment_metadata_flag = segment_metadata_flag
        self.source_entity_id = source_entity_id
        self.transaction_seq_num = transaction_seq_num
        self.dest_entity_id = dest_entity_id

    def set_large_file_flag(self, large: bool):
        self.large_file = large

    def set_pdu_data_field_length(self, new_length: int):
        self.pdu_data_field_length = new_length

    def get_packet_len(self) -> int:
        """Get length of PDU header when packing it"""
        return self.FIXED_LENGTH + 2 * self.len_entity_id + self.len_transaction_seq_num

    def pack(self) -> bytearray:
        header = bytearray()
        header.append(
            self.VERSION_BITS | (self.pdu_type << 4) | (self.direction << 3) |
            (self.trans_mode << 2) | (self.crc_flag << 1) | self.large_file
        )
        header.append((self.pdu_data_field_length >> 8) & 0xff)
        header.append(self.pdu_data_field_length & 0xff)
        header.append(
            self.segmentation_control << 7 | self.len_entity_id << 4 |
            self.segment_metadata_flag << 3 | self.len_transaction_seq_num
        )
        header.extend(self.source_entity_id)
        header.extend(self.transaction_seq_num)
        header.extend(self.dest_entity_id)
        return header

    @classmethod
    def __empty(cls) -> PduHeader:
        return cls(
            pdu_type=PduType.FILE_DIRECTIVE,
            trans_mode=TransmissionModes.UNACKNOWLEDGED,
            segment_metadata_flag=SegmentMetadataFlag.NOT_PRESENT,
            transaction_seq_num=bytes([0])
        )

    @classmethod
    def unpack(cls, raw_packet: bytearray) -> PduHeader:
        """Unpack a raw bytearray into the PDU header object representation

        :param raw_packet:
        :raise ValueError: Passed bytearray is too short.
        :return:
        """
        if len(raw_packet) < cls.FIXED_LENGTH:
            LOGGER.warning('Can not unpack less than four bytes into PDU header')
            raise ValueError
        pdu_header = cls.__empty()
        pdu_header.pdu_type = raw_packet[0] & 0x10
        pdu_header.direction = raw_packet[0] & 0x08
        pdu_header.trans_mode = raw_packet[0] & 0x04
        pdu_header.crc_flag = raw_packet[0] & 0x02
        pdu_header.large_file = raw_packet[0] & 0x01
        pdu_header.pdu_data_field_length = raw_packet[1] << 8 | raw_packet[2]
        pdu_header.segmentation_control = raw_packet[3] & 0x80
        pdu_header.len_entity_id = cls.check_len_in_bytes(raw_packet[3] & 0x70)
        pdu_header.segment_metadata_flag = raw_packet[3] & 0x08
        pdu_header.len_transaction_seq_num = cls.check_len_in_bytes(raw_packet[3] & 0x01)
        expected_remaining_len = 2 * pdu_header.len_entity_id + pdu_header.len_transaction_seq_num
        if len(raw_packet) - cls.FIXED_LENGTH < expected_remaining_len:
            LOGGER.warning('Raw packet too small for PDU header')
            raise ValueError
        current_idx = 4
        pdu_header.source_entity_id = \
            raw_packet[current_idx: current_idx + pdu_header.len_entity_id]
        current_idx += pdu_header.len_entity_id
        pdu_header.transaction_seq_num = \
            raw_packet[current_idx: current_idx + pdu_header.len_transaction_seq_num]
        current_idx += pdu_header.len_transaction_seq_num
        pdu_header.dest_entity_id = \
            raw_packet[current_idx: current_idx + pdu_header.len_entity_id]
        return pdu_header

    @staticmethod
    def check_len_in_bytes(detected_len: int) -> LenInBytes:
        try:
            len_in_bytes = LenInBytes(detected_len)
        except ValueError:
            LOGGER.warning(
                'Unsupported length field detected. '
                'Only 1, 2, 4 and 8 bytes are supported'
            )
            raise ValueError
        return len_in_bytes
