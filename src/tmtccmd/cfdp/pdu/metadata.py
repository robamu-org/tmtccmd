from __future__ import annotations
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
        source_file_name_as_bytes = source_file_name.encode('utf-8')
        self.source_file_name_lv = CfdpLv(
            value=source_file_name_as_bytes
        )
        dest_file_name_as_bytes = dest_file_name.encode('utf-8')
        self.dest_file_name_lv = CfdpLv(
            value=dest_file_name_as_bytes
        )
        self.options = options

    @classmethod
    def __empty(cls) -> MetadataPdu:
        cls(
            closure_requested=None,
            checksum_type=None,
            file_size=None,
            source_file_name="",
            dest_file_name="",
            direction=None,
            trans_mode=None
        )

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

    @classmethod
    def unpack(cls, raw_packet: bytearray) -> MetadataPdu:
        metadata_pdu = cls.__empty()
        metadata_pdu.pdu_file_directive = FileDirectivePduBase.unpack(raw_packet=raw_packet)
        current_idx = metadata_pdu.pdu_file_directive.get_len()
        # Minimal length: 1 byte + FSS (4 byte) + 2 empty LV (1 byte)
        if not check_packet_length(len(raw_packet), metadata_pdu.pdu_file_directive.get_len() + 7):
            raise ValueError
        metadata_pdu.closure_requested = raw_packet[current_idx] & 0x40
        metadata_pdu.checksum_type = raw_packet[current_idx] & 0x0f
        current_idx += 1
        current_idx, metadata_pdu.file_size = metadata_pdu.pdu_file_directive.parse_fss_field(
            raw_packet=raw_packet, current_idx=current_idx
        )
        metadata_pdu.source_file_name_lv.unpack(raw_bytes=raw_packet[current_idx:])
        current_idx += metadata_pdu.source_file_name_lv.get_len()
        metadata_pdu.dest_file_name_lv.unpack(raw_bytes=raw_packet[current_idx:])
        current_idx += metadata_pdu.dest_file_name_lv.get_len()
        if current_idx < len(raw_packet):
            metadata_pdu.parse_options(raw_packet=raw_packet, start_idx=current_idx)
        return metadata_pdu

    def parse_options(self, raw_packet: bytearray, start_idx: int):
        self.options = []
        current_idx = start_idx
        while True:
            current_tlv = CfdpTlv(serialize=False)
            current_tlv.unpack(raw_bytes=raw_packet[current_idx])
            self.options.append(current_tlv)
            # This will always increment at least two, so we can't get stuck in the loop
            current_idx += current_tlv.get_total_length()
            if current_idx > len(raw_packet):
                LOGGER.warning(
                    'Parser Error when parsing TLVs in Finished PDU. '
                    'Possibly invalid packet'
                )
                break
            elif current_idx == len(raw_packet):
                break
