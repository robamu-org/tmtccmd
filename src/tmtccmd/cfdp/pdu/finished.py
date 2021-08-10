from tmtccmd.cfdp.pdu.file_directive import FileDirectivePduBase, DirectiveCodes, Direction, \
    TransmissionModes, CrcFlag, ConditionCode
from tmtccmd.cfdp.conf import LenInBytes
from tmtccmd.cfdp.tlv import CfdpTlv
from typing import List


class DeliveryCode(enum.IntEnum):
    DATA_COMPLETE = 0
    DATA_INCOMPLETE = 1


class FileDeliveryStatus(enum.IntEnum):
    DISCARDED_DELIBERATELY = 0
    DISCARDED_FILESTORE_REJECTION = 1
    FILE_RETAINED = 2
    FILE_STATUS_UNREPORTED = 3


class FinishedPdu():
    def __init__(
            self,
            serialize: bool,
            direction: Direction,
            delivery_code: DeliveryCode,
            file_delivery_status: FileDeliveryStatus,
            trans_mode: TransmissionModes,
            condition_code: ConditionCode = ConditionCode.NO_ERROR,
            file_store_responses: List[CfdpTlv] = [],
            fault_location: CfdpTlv = None,
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
        self.pdu_file_directive.condition_code = condition_code
        self.delivery_code = delivery_code
        self.file_store_responses = file_store_responses
        self.fault_location = fault_location
        self.file_delivery_status = file_delivery_status

    def pack(self) -> bytearray:
        packet = self.pdu_file_directive.pack()
        packet[len(packet) - 1] |= (self.delivery_code << 2) | self.file_delivery_status
        for file_store_reponse in self.file_store_responses:
            packet.extend(file_store_reponse.pack())
        if self.fault_location is not None:
            packet.extend(self.fault_location.pack())
        return packet

    def unpack(self, raw_packet: bytearray):
        self.pdu_file_directive.unpack(raw_bytes=raw_packet)
