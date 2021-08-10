from tmtccmd.cfdp.pdu.file_directive import FileDirectivePduBase, DirectiveCodes, Direction, \
    TransmissionModes, CrcFlag
from tmtccmd.cfdp.conf import LenInBytes


class FinishedPdu():
    def __init__(
            self,
            serialize: bool,
            direction: Direction,
            trans_mode: TransmissionModes,
            crc_flag: CrcFlag = CrcFlag.GLOBAL_CONFIG,
            len_entity_id: LenInBytes = LenInBytes.NONE,
            len_transaction_seq_num: LenInBytes = LenInBytes.NONE
    ):
        self.pdu_file_directive = FileDirectivePduBase(
            serialize=serialize,
            directive_code=DirectiveCodes.FINISHED_PDU,
            direction=direction,
            trans_mode=trans_mode,
            crc_flag=crc_flag,
            len_entity_id=len_entity_id,
            len_transaction_seq_num=len_transaction_seq_num
        )