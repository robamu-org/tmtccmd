from tmtccmd.ccsds.handler import CcsdsTmHandler
from tmtccmd.utility.logger import get_console_logger

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


class LenInBytes(enum.IntEnum):
    ONE_BYTE = 0
    TWO_BYTES = 1
    THREE_BYTES = 2
    FOUR_BYTES = 3
    FIVE_BYTES = 4
    SIX_BYTES = 5
    SEVEN_BYTES = 6
    EIGHT_BYTES = 7


class SegmentMetadataFlag(enum.IntEnum):
    """Aways 0 and ignored for File Directive PDUs (CCSDS 727.0-B-5 p.75)"""
    NOT_PRESENT = 0
    PRESENT = 1


class SegmentationControl(enum.IntEnum):
    """Aways 0 and ignored for File Directive PDUs (CCSDS 727.0-B-5 p.75)"""
    NO_RECORD_BOUNDARIES_PRESERVATION = 0
    RECORD_BOUNDARIES_PRESERVATION = 1


class PduHeader:
    VERSION_BITS = 0b0010_0000

    """This class encapsulates the fixed-format PDU header.
    For more, information, refer to CCSDS 727.0-B-5 p.75"""
    def __init__(
            self, pdu_type: PduType, direction: Direction, trans_mode: TransmissionModes,
            crc_flag: CrcFlag, seg_ctrl = SegmentationControl.NO_RECORD_BOUNDARIES_PRESERVATION,
            len_entity_id: LenInBytes = LenInBytes.FOUR_BYTES,
            segment_metadata_flag = SegmentMetadataFlag.NOT_PRESENT,
            len_transaction_seq_num = LenInBytes.TWO_BYTES
    ):
        self.pdu_type = pdu_type
        self.direction = direction
        self.trans_mode = trans_mode
        self.crc_flag = crc_flag
        self.large_file = False
        self.pdu_data_field_length = 0
        self.segmentation_control = seg_ctrl
        self.len_entity_id = entity_id_len
        self.segment_metadata_flag = segment_metadata_flag
        self.len_transaction_seq_num = len_transaction_seq_num

    def set_large_file_flag(self):
        self.large_file = True

    def set_pdu_data_field_length(self, new_length: int):
        self.pdu_data_field_length = new_length

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

    def unpack(self, raw_bytes: bytearray):
        if len(raw_bytes) < 4:
            LOGGER.warning('Can not unpack less than four bytes into PDU header')
            return
        self.pdu_type = raw_bytes[0] & 0x10
        self.direction = raw_bytes[0] & 0x08
        self.trans_mode = raw_bytes[0] & 0x04
        self.crc_flag = raw_bytes[0] & 0x02
        self.large_file = raw_bytes[0] & 0x01
        self.pdu_data_field_length = raw_bytes[1] << 8 | raw_bytes[2]
        self.segmentation_control = raw_bytes[3] & 0x80
        self.len_entity_id = raw_bytes[3] & 0x70
        self.segment_metadata_flag = raw_bytes[3] & 0x08
        self.len_transaction_seq_num = raw_bytes[3] & 0x01
