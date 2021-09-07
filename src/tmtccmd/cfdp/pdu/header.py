from __future__ import annotations
import enum

from tmtccmd.ccsds.handler import CcsdsTmHandler
from tmtccmd.utility.logger import get_console_logger
from tmtccmd.cfdp.definitions import LenInBytes
from tmtccmd.cfdp.conf import get_default_length_entity_id, \
    get_default_length_transaction_seq_num, get_default_pdu_crc_mode


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
    """Aways 0 and ignored for File Directive PDUs (CCSDS 727.0-B-5 p.75)"""
    NO_RECORD_BOUNDARIES_PRESERVATION = 0
    RECORD_BOUNDARIES_PRESERVATION = 1


class PduHeader:
    VERSION_BITS = 0b0010_0000

    """This class encapsulates the fixed-format PDU header.
    For more, information, refer to CCSDS 727.0-B-5 p.75"""
    def __init__(
            self,
            pdu_type: PduType,
            direction: Direction,
            trans_mode: TransmissionModes,
            crc_flag: CrcFlag = CrcFlag.GLOBAL_CONFIG,
            len_entity_id: LenInBytes = LenInBytes.NONE,
            len_transaction_seq_num: LenInBytes = LenInBytes.NONE,
            seg_ctrl: SegmentationControl = SegmentationControl.NO_RECORD_BOUNDARIES_PRESERVATION,
            segment_metadata_flag: SegmentMetadataFlag = SegmentMetadataFlag.NOT_PRESENT,
    ):
        """Constructor for PDU header
        :param serialize: Specify whether a packet will be serialized or deserialized
        :param pdu_type:
        :param direction:
        :param trans_mode:
        :param crc_flag: If not supplied, assign the default configuration
        :param len_entity_id: If not suplied, the default configuration will be used
        :param len_transaction_seq_num: If not supplied, the default configuration will be used
        :param seg_ctrl:
        :param segment_metadata_flag:
        :raise ValueError: If some field were not specified with serialize == True
        """
        self.pdu_type = pdu_type
        self.direction = direction
        self.trans_mode = trans_mode
        self.large_file = False
        self.pdu_data_field_length = 0
        self.segmentation_control = seg_ctrl
        if len_entity_id is LenInBytes.NONE:
            self.len_entity_id = get_default_length_entity_id()
        else:
            self.len_entity_id = len_entity_id
        if len_transaction_seq_num is LenInBytes.NONE:
            self.len_transaction_seq_num = get_default_length_transaction_seq_num()
        else:
            self.len_transaction_seq_num = len_transaction_seq_num
        if crc_flag == CrcFlag.GLOBAL_CONFIG:
            self.crc_flag = get_default_pdu_crc_mode()
        else:
            self.crc_flag = crc_flag
        self.segment_metadata_flag = segment_metadata_flag

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
        return header

    @classmethod
    def unpack(cls, raw_packet: bytearray) -> PduHeader:
        """Unpack a raw bytearray into the PDU header oject representation
        :param raw_packet:
        :raise ValueError: Passed bytearray is too short.
        :return:
        """
        if len(raw_packet) < 4:
            LOGGER.warning('Can not unpack less than four bytes into PDU header')
            raise ValueError
        pdu_type = raw_packet[0] & 0x10
        direction = raw_packet[0] & 0x08
        trans_mode = raw_packet[0] & 0x04
        crc_flag = raw_packet[0] & 0x02
        large_file = raw_packet[0] & 0x01
        pdu_data_field_length = raw_packet[1] << 8 | raw_packet[2]
        segmentation_control = raw_packet[3] & 0x80
        len_entity_id = raw_packet[3] & 0x70
        segment_metadata_flag = raw_packet[3] & 0x08
        len_transaction_seq_num = raw_packet[3] & 0x01

        return cls(
            pdu_type=pdu_type,
            direction=direction,
            trans_mode=trans_mode,
            crc_flag=crc_flag,
            large_file=large_file,
            pdu_data_field_length=pdu_data_field_length,
            segmentation_control=segmentation_control,
            len_entity_id=len_entity_id,
            segment_metadata_flag=segment_metadata_flag,
            len_transaction_seq_num=len_transaction_seq_num
        )
