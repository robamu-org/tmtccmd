from tmtccmd.cfdp.pdu.file_directive import FileDirectivePduBase, DirectiveCodes, ConditionCode
from tmtccmd.cfdp.pdu.header import Direction, TransmissionModes, CrcFlag
from tmtccmd.cfdp.tlv import CfdpTlv
from tmtccmd.cfdp.conf import LenInBytes


class EofPdu():
    def __init__(
        self,
        serialize: bool,
        file_checksum: int,
        file_size: int,
        direction: Direction,
        trans_mode: TransmissionModes,
        crc_flag: CrcFlag,
        fault_location: CfdpTlv = None,
        condition_code: ConditionCode = ConditionCode.NO_ERROR,
        len_entity_id: LenInBytes = LenInBytes.NONE,
        len_transaction_seq_num=LenInBytes.NONE,
    ):
        self.pdu_file_directive = FileDirectivePduBase(
            serialize=serialize,
            directive_code=DirectiveCodes.EOF_PDU,
            direction=direction,
            trans_mode=trans_mode,
            crc_flag=crc_flag,
            len_entity_id=len_entity_id,
            len_transaction_seq_num=len_transaction_seq_num
        )
        self.pdu_file_directive.condition_code = condition_code
        self.file_checksum = file_checksum
        self.file_size = file_size
        self.fault_location = fault_location

    def pack(self):
        pass

    def unpack(self, raw_bytes: bytearray):
        self.pdu_file_directive.unpack(raw_bytes=raw_bytes)
