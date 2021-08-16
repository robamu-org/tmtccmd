import struct

from tmtccmd.cfdp.pdu.file_directive import FileDirectivePduBase, DirectiveCodes, \
    ConditionCode
from tmtccmd.cfdp.pdu.header import Direction, TransmissionModes, CrcFlag
from tmtccmd.cfdp.tlv import CfdpTlv
from tmtccmd.cfdp.conf import LenInBytes, check_packet_length
from tmtccmd.ccsds.log import LOGGER


class EofPdu():
    MINIMAL_LENGTH = FileDirectivePduBase.FILE_DIRECTIVE_PDU_LEN + 1 + 4 + 4

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
        self.condition_code = condition_code
        self.file_checksum = file_checksum
        self.file_size = file_size
        self.fault_location = fault_location

    def pack(self) -> bytearray:
        eof_pdu = bytearray()
        eof_pdu.extend(self.pdu_file_directive.pack())
        eof_pdu.append(self.condition_code << 4)
        eof_pdu.extend(struct.pack('!I', self.file_checksum))
        if self.pdu_file_directive.pdu_header.large_file:
            eof_pdu.extend(struct.pack('!Q', self.file_size))
        else:
            eof_pdu.extend(struct.pack('!I', self.file_size))
        if self.fault_location is not None:
            eof_pdu.extend(self.fault_location.pack())
        return eof_pdu

    def unpack(self, raw_packet: bytearray):
        """Deserialize raw EOF PDU packet
        :param raw_packet:
        :raise ValueError: If raw packet is too short
        :return:
        """
        self.pdu_file_directive.unpack(raw_packet=raw_packet)
        expected_min_len = self.MINIMAL_LENGTH
        if not check_packet_length(raw_packet_len=len(raw_packet), min_len=expected_min_len):
            raise ValueError
        current_idx = self.pdu_file_directive.get_len()
        self.condition_code = raw_packet[current_idx] & 0xf0
        expected_min_len = self.pdu_file_directive.get_len() + 5
        current_idx += 1
        checksum_raw = raw_packet[current_idx: current_idx + 4]
        self.file_checksum = struct.unpack('!I', checksum_raw)[0]
        current_idx += 4
        current_idx, self.file_size = self.pdu_file_directive.parse_fss_field(
            raw_packet=raw_packet, current_idx=current_idx
        )
        if len(raw_packet) > current_idx:
            self.fault_location = CfdpTlv(serialize=False)
            self.fault_location.unpack(raw_bytes=raw_packet[current_idx:])
