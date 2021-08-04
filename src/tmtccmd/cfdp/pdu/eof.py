from tmtccmd.cfdp.pdu.file_directive import FileDirectivePduBase, DirectiveCodes


class EofPdu():
    def __init__(
        self,
        # PDU Header parameters
        direction: Direction,
        trans_mode: TransmissionModes,
        crc_flag: CrcFlag,
        len_entity_id: LenInBytes = LenInBytes.NONE,
        len_transaction_seq_num=LenInBytes.NONE,
    ):
        self.pdu_file_directive = FileDirectivePduBase(
            directive_code=DirectiveCodes.EOF_PDU,
            direction=direction,
            trans_mode=trans_mode,
            crc_flag=crc_flag,
            len_entity_id=len_entity_id,
            len_transaction_seq_num=len_transaction_seq_num
        )

    def pack(self):
        pass

    def unpack(self, raw_bytes: bytearray):
        self.pdu_file_directive.unpack(raw_bytes=raw_bytes)
