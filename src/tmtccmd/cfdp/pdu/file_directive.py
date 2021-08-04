from .header import PduHeader, PduType, Direction, CrcFlag


class DirectiveCodes(enum.IntEnum):
    EOF_PDU = 0x04
    FINISHED_PDU = 0x05
    ACK_PDU = 0x06
    METADATA_PDU = 0x07
    NAK_PDU = 0x08
    PROMPT_PDU = 0x09
    KEEP_ALIVE_PDU = 0x0C


class ConditionCode(enum.IntEnum):
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
    """Base class for file directive PDUs encapsulating all its common components.
    All other file directive PDU classes implement this class
    """
    def __init__(
            self, directive_code: DirectiveCodes,
            # PDU Header parameters
            direction: Direction,
            trans_mode: TransmissionModes,
            crc_flag: CrcFlag,
            len_entity_id: LenInBytes = LenInBytes.NONE,
            len_transaction_seq_num=LenInBytes.NONE,
    ):
        self.pdu_header = PduHeader(
            pdu_type=PduType.FILE_DIRECTIVE, direction=direction, trans_mode=trans_mode,
            crc_flag=crc_flag, len_entity_id=len_entity_id,
            len_transaction_seq_num=len_transaction_seq_num
        )
        self.directive_code = directive_code
        self.condition_code = 0

    def pack(self) -> bytearray:
        data = bytearray()
        data.extend(self.pdu_header.pack())
        data.append(self.directive_code)
        return data

    def unpack(self, raw_bytes: bytearray):
        """Unpack a raw bytearray into the File Directive DPU object representation
        :param raw_bytes:
        :raise ValueError: Passed bytearray is too short.
        :return:
        """
        self.pdu_header.unpack(raw_bytes=raw_bytes)
        if len(raw_bytes) < 5:
            LOGGER.warning('Can not unpack less than five bytes into File Directive PDU')
            raise ValueError
        self.directive_code = raw_bytes[4]