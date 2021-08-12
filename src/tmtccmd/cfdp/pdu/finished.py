import enum

from tmtccmd.cfdp.pdu.file_directive import FileDirectivePduBase, DirectiveCodes, Direction, \
    TransmissionModes, CrcFlag, ConditionCode
from tmtccmd.cfdp.definitions import LenInBytes
from tmtccmd.cfdp.conf import check_packet_length, LOGGER
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
    MINIMAL_LEN = FileDirectivePduBase.FILE_DIRECTIVE_PDU_LEN + 1

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
        self.condition_code = condition_code
        self.delivery_code = delivery_code
        self.file_store_responses = file_store_responses
        self.fault_location = fault_location
        self.file_delivery_status = file_delivery_status
        self.might_have_fault_location = False
        if self.condition_code != ConditionCode.NO_ERROR and \
            self.condition_code != ConditionCode.UNSUPPORTED_CHECKSUM_TYPE:
            self.might_have_fault_location = True

    def pack(self) -> bytearray:
        packet = self.pdu_file_directive.pack()
        packet[len(packet)] |= \
            (self.condition_code << 4) | (self.delivery_code << 2) | self.file_delivery_status
        for file_store_reponse in self.file_store_responses:
            packet.extend(file_store_reponse.pack())
        if self.fault_location is not None:
            packet.extend(self.fault_location.pack())
        return packet

    def unpack(self, raw_packet: bytearray):
        """Unpack a raw packet into a PDU object
        :param raw_packet:
        :raise ValueError: If packet is too short
        :return:
        """
        self.pdu_file_directive.unpack(raw_bytes=raw_packet)
        if not check_packet_length(raw_packet_len=len(raw_packet), min_len=self.MINIMAL_LEN):
            raise ValueError
        current_idx = self.pdu_file_directive.get_len()
        first_param_byte = raw_packet[current_idx]
        self.condition_code =  first_param_byte & 0xf0
        self.delivery_code = first_param_byte & 0x04
        self.file_delivery_status = first_param_byte & 0b11
        current_idx += 1
        if len(raw_packet) > current_idx:
            self.unpack_tlvs(raw_packet=raw_packet, start_idx=current_idx)

    def unpack_tlvs(self, raw_packet: bytearray, start_idx: int) -> int:
        current_idx = start_idx
        while True:
            current_tlv = CfdpTlv(serialize=False)
            current_tlv.unpack(raw_bytes=raw_packet[current_idx])
            # This will always increment at least two, so we can't get stuck in the loop
            current_idx += current_tlv.get_total_length()
            if start_idx > len(raw_packet) or current_idx == len(raw_packet):
                if current_idx > len(raw_packet):
                    LOGGER.warning(
                        'Parser Error when parsing TLVs in Finished PDU. Possibly invalid packet'
                    )
                if self.might_have_fault_location:
                    self.fault_location = current_tlv
                else:
                    self.file_store_responses.append(current_tlv)
                break
            else:
                # Another TLV might follow, so this is a file store response
                self.file_store_responses.append(current_tlv)
        return current_idx
