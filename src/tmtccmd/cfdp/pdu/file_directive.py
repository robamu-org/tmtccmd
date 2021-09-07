from __future__ import annotations
import enum
import struct

from tmtccmd.cfdp.pdu.header import PduHeader, PduType, Direction, CrcFlag, TransmissionModes
from tmtccmd.cfdp.conf import check_packet_length
from tmtccmd.cfdp.definitions import LenInBytes
from tmtccmd.ccsds.log import LOGGER


class DirectiveCodes(enum.IntEnum):
    EOF_PDU = 0x04
    FINISHED_PDU = 0x05
    ACK_PDU = 0x06
    METADATA_PDU = 0x07
    NAK_PDU = 0x08
    PROMPT_PDU = 0x09
    KEEP_ALIVE_PDU = 0x0C


class ConditionCode(enum.IntEnum):
    NO_CONDITION_FIELD = -1
    NO_ERROR = 0b0000
    POSITIVE_ACK_LIMIT_REACHED = 0b0001
    KEEP_ALIVE_LIMIT_REACHED = 0b0010
    INVALID_TRANSMISSION_MODE = 0b0011
    FILESTORE_REJECTION = 0b0100
    FILE_CHECKSUM_FAILURE = 0b0101
    FILE_SIZE_ERROR = 0b0110
    NAK_LIMIT_REACHED = 0b0111
    INACTIVITY_DETECTED = 0b1000
    CHECK_LIMIT_REACHED = 0b1010
    UNSUPPORTED_CHECKSUM_TYPE = 0b1011
    SUSPEND_REQUEST_RECEIVED = 0b1110
    CANCEL_REQUEST_RECEIVED = 0b1111


class FileDirectivePduBase:
    FILE_DIRECTIVE_PDU_LEN = 5
    """Base class for file directive PDUs encapsulating all its common components.
    All other file directive PDU classes implement this class
    """
    def __init__(
            self,
            directive_code: DirectiveCodes,
            # PDU Header parameters
            direction: Direction,
            trans_mode: TransmissionModes,
            crc_flag: CrcFlag,
            len_entity_id: LenInBytes = LenInBytes.NONE,
            len_transaction_seq_num: LenInBytes = LenInBytes.NONE,
    ):
        self.pdu_header = PduHeader(
            pdu_type=PduType.FILE_DIRECTIVE,
            direction=direction,
            trans_mode=trans_mode,
            crc_flag=crc_flag,
            len_entity_id=len_entity_id,
            len_transaction_seq_num=len_transaction_seq_num
        )
        self.directive_code = directive_code

    @classmethod
    def __empty(cls) -> FileDirectivePduBase:
        return cls(
            directive_code=None,
            direction=None,
            trans_mode=None,
            crc_flag=None
        )

    def get_len(self) -> int:
        return self.FILE_DIRECTIVE_PDU_LEN

    def pack(self) -> bytearray:
        data = bytearray()
        data.extend(self.pdu_header.pack())
        data.append(self.directive_code)
        return data

    @classmethod
    def unpack(cls, raw_packet: bytearray) -> FileDirectivePduBase:
        """Unpack a raw bytearray into the File Directive PDU object representation
        :param raw_bytes:
        :raise ValueError: Passed bytearray is too short.
        :return:
        """
        file_directive = cls.__empty()
        file_directive.pdu_header = PduHeader.unpack(raw_packet=raw_packet)
        if not check_packet_length(raw_packet_len=len(raw_packet), min_len=5):
            raise ValueError
        file_directive.directive_code = raw_packet[4]
        return file_directive

    def verify_file_len(self, file_size: int) -> bool:
        if self.pdu_file_directive.pdu_header.large_file and file_size > pow(2, 64):
            LOGGER.warning(f'File size {file_size} larger than 64 bit field')
            raise False
        elif not self.pdu_file_directive.pdu_header.large_file and file_size > pow(2, 32):
            LOGGER.warning(f'File size {file_size} larger than 32 bit field')
            raise False
        return True

    def parse_fss_field(self, raw_packet: bytearray, current_idx: int) -> (int, int):
        """Parse the FSS field, which has different size depending on the large file flag being
        set or not. Returns the current index incremented and the parsed file size
        :raise ValueError: Packet not large enough
        """
        if self.pdu_header.large_file:
            if not check_packet_length(len(raw_packet), current_idx + 8 + 1):
                raise ValueError
            file_size = struct.unpack('!I', raw_packet[current_idx: current_idx + 8])
            current_idx += 8
        else:
            if not check_packet_length(len(raw_packet), current_idx + 4 + 1):
                raise ValueError
            file_size = struct.unpack('!I', raw_packet[current_idx: current_idx + 4])
            current_idx += 4
        return current_idx, file_size
