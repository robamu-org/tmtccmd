import struct

from tmtccmd.cfdp.pdu.file_directive import FileDirectivePduBase, DirectiveCodes, \
    ConditionCode
from tmtccmd.cfdp.pdu.header import Direction, TransmissionModes, CrcFlag
from tmtccmd.cfdp.tlv import CfdpTlv
from tmtccmd.cfdp.definitions import LenInBytes, ChecksumTypes
from tmtccmd.cfdp.conf import check_packet_length
from tmtccmd.ccsds.log import LOGGER


class MetadataPdu():
    def __init__(
        self,
        serialize: bool,
        closure_requested: bool,
        checksum_type: ChecksumTypes,
        file_size: int,
        direction: Direction,
        trans_mode: TransmissionModes,
        crc_flag: CrcFlag = CrcFlag.GLOBAL_CONFIG,
        len_entity_id: LenInBytes = LenInBytes.NONE,
        len_transaction_seq_num=LenInBytes.NONE,
    ):
        self.pdu_file_directive = FileDirectivePduBase(
            serialize=serialize,
            directive_code=DirectiveCodes.METADATA_PDU,
            direction=direction,
            trans_mode=trans_mode,
            crc_flag=crc_flag,
            len_entity_id=len_entity_id,
            len_transaction_seq_num=len_transaction_seq_num
        )
        self.closure_requested = closure_requested
        self.checksum_type = checksum_type
        self.file_size = file_size