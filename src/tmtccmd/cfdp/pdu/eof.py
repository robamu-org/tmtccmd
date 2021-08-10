import struct

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
        crc_flag: CrcFlag = CrcFlag.GLOBAL_CONFIG,
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

    def pack(self) -> bytearray:
        eof_pdu = bytearray()
        eof_pdu.extend(self.pdu_file_directive.pack())
        eof_pdu.append(self.pdu_file_directive.condition_code << 4)
        eof_pdu.extend(struct.pack('!I', self.file_checksum))
        if self.pdu_file_directive.pdu_header.large_file:
            eof_pdu.extend(struct.pack('!Q', self.file_size))
        else:
            eof_pdu.extend(struct.pack('!I', self.file_size))
        if self.fault_location is not None:
            eof_pdu.extend(self.fault_location.pack())
        return eof_pdu

    def unpack(self, raw_bytes: bytearray):
        self.pdu_file_directive.unpack(raw_bytes=raw_bytes)
