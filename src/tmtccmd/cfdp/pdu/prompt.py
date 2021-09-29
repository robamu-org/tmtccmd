from __future__ import annotations
import enum

from tmtccmd.cfdp.pdu.file_directive import FileDirectivePduBase, DirectiveCodes, Direction, \
    TransmissionModes, CrcFlag, ConditionCode
from tmtccmd.cfdp.definitions import LenInBytes


class ResponseRequired(enum.IntEnum):
    NAK = 0
    KEEP_ALIVE = 1


class PromptPdu():
    def __init__(
        self,
        reponse_required: ResponseRequired,
        # PDU file directive arguments
        direction: Direction,
        trans_mode: TransmissionModes,
        crc_flag: CrcFlag = CrcFlag.GLOBAL_CONFIG,
        len_entity_id: LenInBytes = LenInBytes.NONE,
        len_transaction_seq_num=LenInBytes.NONE,
    ):
        self.pdu_file_directive = FileDirectivePduBase(
            directive_code=DirectiveCodes.PROMPT_PDU,
            direction=direction,
            trans_mode=trans_mode,
            crc_flag=crc_flag,
            len_entity_id=len_entity_id,
            len_transaction_seq_num=len_transaction_seq_num
        )
        self.response_required = reponse_required

    @classmethod
    def __empty(cls) -> PromptPdu:
        return cls(
            reponse_required=None,
            direction=None,
            trans_mode=None,
            start_of_scope=None,
            end_of_scope=None,
            segment_requests=None
        )

    def pack(self) -> bytearray:
        prompt_pdu = self.pdu_file_directive.pack()
        prompt_pdu.append(self.response_required << 7)
        return prompt_pdu

    @classmethod
    def unpack(cls, raw_packet: bytearray) -> PromptPdu:
        prompt_pdu = cls.__empty()
        prompt_pdu.pdu_file_directive = FileDirectivePduBase.unpack(raw_packet=raw_packet)
        current_idx = prompt_pdu.pdu_file_directive.get_len()
        prompt_pdu.response_required = raw_packet[current_idx] & 0x80
        return prompt_pdu
