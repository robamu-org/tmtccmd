from __future__ import annotations

import struct

from tmtccmd.cfdp.pdu.file_directive import FileDirectivePduBase, DirectiveCodes, Direction, \
    TransmissionModes, CrcFlag, ConditionCode
from tmtccmd.cfdp.definitions import LenInBytes
from tmtccmd.ccsds.log import LOGGER


class KeepAlivePdu():
    """This is a file directive PDU"""

    def __init__(
        self,
        progress: int,
        # PDU file directive arguments
        direction: Direction,
        trans_mode: TransmissionModes,
        crc_flag: CrcFlag = CrcFlag.GLOBAL_CONFIG,
        len_entity_id: LenInBytes = LenInBytes.GLOBAL,
        len_transaction_seq_num=LenInBytes.GLOBAL,
    ):
        self.pdu_file_directive = FileDirectivePduBase(
            directive_code=DirectiveCodes.KEEP_ALIVE_PDU,
            direction=direction,
            trans_mode=trans_mode,
            crc_flag=crc_flag,
            len_entity_id=len_entity_id,
            len_transaction_seq_num=len_transaction_seq_num
        )
        self.progress = progress

    @classmethod
    def __empty(cls) -> KeepAlivePdu:
        return cls(
            progress=None,
            direction=None,
            trans_mode=None,
            start_of_scope=None,
            end_of_scope=None,
            segment_requests=None
        )

    def pack(self) -> bytearray:
        keep_alive_packet = self.pdu_file_directive.pack()
        if not self.pdu_file_directive.pdu_header.large_file:
            if self.progress > pow(2, 32) - 1:
                raise ValueError
            keep_alive_packet.extend(struct.pack('I', self.progress))
        else:
            keep_alive_packet.extend(struct.pack('Q', self.progress))
        return keep_alive_packet

    @classmethod
    def unpack(cls, raw_packet: bytearray) -> KeepAlivePdu:
        keep_alive_pdu = cls.__empty()
        keep_alive_pdu.pdu_file_directive = FileDirectivePduBase.unpack(raw_packet=raw_packet)
        current_idx = keep_alive_pdu.pdu_file_directive.get_len()
        if not keep_alive_pdu.pdu_file_directive.pdu_header.large_file:
            struct_arg_tuple = ('!I', 4)
        else:
            struct_arg_tuple = ('!Q', 8)
        if (len(raw_packet) - current_idx) < struct_arg_tuple[1]:
            LOGGER.warning(f'Invalid length {len(raw_packet)} for Keep Alive PDU')
            raise ValueError
        keep_alive_pdu.progress = struct.unpack(
            struct_arg_tuple[0], raw_packet[current_idx: current_idx + struct_arg_tuple[1]]
        )
        return keep_alive_pdu
