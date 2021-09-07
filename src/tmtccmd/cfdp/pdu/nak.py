from __future__ import annotations
import enum
import struct
from typing import List, Tuple

from tmtccmd.cfdp.pdu.file_directive import FileDirectivePduBase, DirectiveCodes, \
    ConditionCode
from tmtccmd.cfdp.pdu.header import Direction, TransmissionModes, CrcFlag
from tmtccmd.cfdp.conf import LenInBytes


class NakPdu():
    def __init__(
        self,
        direction: Direction,
        trans_mode: TransmissionModes,
        start_of_scope: int,
        end_of_scope: int,
        segment_requests: List[Tuple[int, int]],
        crc_flag: CrcFlag = CrcFlag.GLOBAL_CONFIG,
        len_entity_id: LenInBytes = LenInBytes.NONE,
        len_transaction_seq_num=LenInBytes.NONE,
    ):
        self.pdu_file_directive = FileDirectivePduBase(
            directive_code=DirectiveCodes.ACK_PDU,
            direction=direction,
            trans_mode=trans_mode,
            crc_flag=crc_flag,
            len_entity_id=len_entity_id,
            len_transaction_seq_num=len_transaction_seq_num
        )
        self.start_of_scope = start_of_scope
        self.end_of_scope = end_of_scope
        self.segment_requests = segment_requests

    @classmethod
    def __empty(cls) -> NakPdu:
        return cls(
            direction=None,
            trans_mode=None,
            start_of_scope=None,
            end_of_scope=None,
            segment_requests=None
        )

    def pack(self) -> bytearray:
        nak_pdu = self.pdu_file_directive.pack()
        if not self.pdu_file_directive.pdu_header.large_file:
            nak_pdu.extend(struct.pack('!I', self.start_of_scope))
            nak_pdu.extend(struct.pack('!I', self.end_of_scope))
        else:
            nak_pdu.extend(struct.pack('!Q', self.start_of_scope))
            nak_pdu.extend(struct.pack('!Q', self.end_of_scope))
        for segment_request in self.segment_requests:
            if not self.pdu_file_directive.pdu_header.large_file:
                nak_pdu.extend(struct.pack('!I', segment_request[0]))
                nak_pdu.extend(struct.pack('!I', segment_request[1]))
            else:
                nak_pdu.extend(struct.pack('!Q', segment_request[0]))
                nak_pdu.extend(struct.pack('!Q', segment_request[1]))

    @classmethod
    def unpack(cls, raw_packet: bytearray) -> NakPdu:
        nak_pdu = cls.__empty()
        nak_pdu.pdu_file_directive = FileDirectivePduBase.unpack(raw_packet=raw_packet)
        current_idx = nak_pdu.pdu_file_directive.get_len()
        # TODO: Implement
