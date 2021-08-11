import enum
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
            serialize: bool,
            directive_code: DirectiveCodes = None,
            # PDU Header parameters
            direction: Direction = None,
            trans_mode: TransmissionModes = None,
            crc_flag: CrcFlag = None,
            len_entity_id: LenInBytes = LenInBytes.NONE,
            len_transaction_seq_num: LenInBytes = LenInBytes.NONE,
    ):
        if serialize:
            if directive_code is None:
                LOGGER.warning('Some mandatory fields were not specified for serialization')
                raise ValueError
        self.pdu_header = PduHeader(
            serialize=serialize, pdu_type=PduType.FILE_DIRECTIVE, direction=direction,
            trans_mode=trans_mode, crc_flag=crc_flag, len_entity_id=len_entity_id,
            len_transaction_seq_num=len_transaction_seq_num
        )
        self.directive_code = directive_code

    def get_len(self) -> int:
        return self.FILE_DIRECTIVE_PDU_LEN

    def pack(self) -> bytearray:
        data = bytearray()
        data.extend(self.pdu_header.pack())
        data.append(self.directive_code)
        return data

    def unpack(self, raw_packet: bytearray):
        """Unpack a raw bytearray into the File Directive DPU object representation
        :param raw_bytes:
        :raise ValueError: Passed bytearray is too short.
        :return:
        """
        self.pdu_header.unpack(raw_bytes=raw_packet)
        if not check_packet_length(raw_packet_len=len(raw_packet), min_len=5):
            raise ValueError
        self.directive_code = raw_packet[4]
