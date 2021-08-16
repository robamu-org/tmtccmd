import struct
from typing import List

from tmtccmd.cfdp.pdu.file_directive import FileDirectivePduBase, DirectiveCodes, \
    ConditionCode
from tmtccmd.cfdp.pdu.header import Direction, TransmissionModes, CrcFlag
from tmtccmd.cfdp.tlv import CfdpTlv
from tmtccmd.cfdp.lv import CfdpLv
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
        source_file_name: str,
        dest_file_name: str,
        direction: Direction,
        trans_mode: TransmissionModes,
        options: List[CfdpTlv] = [],
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
        source_file_name_as_bytes = source_file_name
        if serialize:
            source_file_name_as_bytes = source_file_name.encode('utf-8')
        self.source_file_name_lv = CfdpLv(
            serialize=serialize, value=source_file_name_as_bytes
        )
        dest_file_name_as_bytes = dest_file_name
        if serialize:
            dest_file_name_as_bytes = dest_file_name.encode('utf-8')
        self.dest_file_name_lv = CfdpLv(
            serialize=serialize, value=dest_file_name_as_bytes
        )
        self.options = options

    def pack(self):
        if not self.pdu_file_directive.verify_file_len(self.file_size):
            raise ValueError
        packet = self.pdu_file_directive.pack()
        current_idx = self.pdu_file_directive.get_len()
        packet.append((self.closure_requested << 6) | self.checksum_type)
        if self.pdu_file_directive.pdu_header.large_file:
            packet.extend(struct.pack('!Q', self.file_size))
        else:
            packet.extend(struct.pack('!I', self.file_size))
        packet.extend(self.source_file_name_lv.pack())
        packet.extend(self.dest_file_name_lv.pack())
        for option in self.options:
            packet.extend(option.pack())

    def unpack(self, raw_packet: bytearray):
        self.pdu_file_directive.unpack(raw_packet=raw_packet)
        current_idx = self.pdu_file_directive.get_len()
        if not check_packet_length(len(raw_packet), self.pdu_file_directive.get_len() + 5):
            raise ValueError
        self.closure_requested = raw_packet[current_idx] & 0x40
        self.checksum_type = raw_packet[current_idx] & 0x0f
        current_idx += 1
        current_idx, self.file_size = self.pdu_file_directive.parse_fss_field(
            raw_packet=raw_packet, current_idx=current_idx
        )
        pass
