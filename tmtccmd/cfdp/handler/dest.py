from __future__ import annotations

import dataclasses
import enum
import logging
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Deque, cast, Optional

from spacepackets.cfdp import (
    PduType,
    ChecksumType,
    TransmissionMode,
    ConditionCode,
    TlvType,
    PduConfig,
    Direction,
    FaultHandlerCode,
)
from spacepackets.cfdp.pdu import (
    DirectiveType,
    AbstractFileDirectiveBase,
    MetadataPdu,
    FileDataPdu,
    EofPdu,
    FinishedPdu,
)
from spacepackets.cfdp.pdu.finished import (
    FinishedParams,
    DeliveryCode,
    FileDeliveryStatus,
)
from spacepackets.cfdp.pdu.helper import GenericPduPacket, PduHolder
from tmtccmd.cfdp import (
    CfdpUserBase,
    LocalEntityCfg,
    RemoteEntityCfgTable,
    RemoteEntityCfg,
)
from tmtccmd.cfdp.defs import CfdpStates, TransactionId
from tmtccmd.cfdp.handler.crc import Crc32Helper
from tmtccmd.cfdp.handler.defs import (
    FileParamsBase,
    PacketSendNotConfirmed,
    NoRemoteEntityCfgFound,
)
from tmtccmd.cfdp.user import (
    MetadataRecvParams,
    FileSegmentRecvdParams,
    TransactionFinishedParams,
)


_LOGGER = logging.getLogger(__name__)


@dataclass
class DestFileParams(FileParamsBase):
    file_name: Path

    @classmethod
    def empty(cls) -> DestFileParams:
        return cls(
            progress=0,
            segment_len=0,
            crc32=bytes(),
            file_size=0,
            file_name=Path(),
            no_file_data=False,
        )

    def reset(self):
        super().reset()
        self.file_name = Path()


class TransactionStep(enum.Enum):
    IDLE = 0
    # Metadata was received
    TRANSACTION_START = 1
    RECEIVING_FILE_DATA = 2
    SENDING_ACK_PDU = 3
    # File transfer complete. Perform checksum verification and notice of completion
    TRANSFER_COMPLETION = 4
    SENDING_FINISHED_PDU = 5


@dataclass
class DestStateWrapper:
    state: CfdpStates = CfdpStates.IDLE
    transaction: TransactionStep = TransactionStep.IDLE
    transaction_id: Optional[TransactionId] = None
    packet_ready: bool = False


@dataclass
class DestFieldWrapper:
    transaction_id: Optional[TransactionId] = None
    remote_cfg: Optional[RemoteEntityCfg] = None
    closure_requested: bool = False
    condition_code: ConditionCode = ConditionCode.NO_CONDITION_FIELD
    delivery_code: DeliveryCode = DeliveryCode.DATA_INCOMPLETE
    file_status: FileDeliveryStatus = FileDeliveryStatus.DISCARDED_DELIBERATELY
    pdu_conf: PduConfig = dataclasses.field(default_factory=lambda: PduConfig.empty())
    fp: DestFileParams = dataclasses.field(
        default_factory=lambda: DestFileParams.empty()
    )
    file_directives_dict: Dict[
        DirectiveType, List[AbstractFileDirectiveBase]
    ] = dataclasses.field(default_factory=lambda: dict())
    file_data_deque: Deque[FileDataPdu] = dataclasses.field(
        default_factory=lambda: deque()
    )

    def reset(self):
        self.transaction_id = None
        self.closure_requested = False
        self.condition_code = ConditionCode.NO_CONDITION_FIELD
        self.delivery_code = DeliveryCode.DATA_INCOMPLETE
        self.pdu_conf = PduConfig.empty()
        self.fp.reset()
        self.remote_cfg = None

    def clear_file_deque(self):
        self.file_data_deque.clear()

    def clear_file_directive_dict(self):
        self.file_directives_dict.clear()


class FsmResult:
    def __init__(self, states: DestStateWrapper, pdu_holder: PduHolder):
        self.states = states
        self.pdu_holder = pdu_holder


class DestHandler:
    def __init__(
        self,
        cfg: LocalEntityCfg,
        user: CfdpUserBase,
        remote_cfg_table: RemoteEntityCfgTable,
    ):
        self.cfg = cfg
        self.remote_cfg_table = remote_cfg_table
        self.states = DestStateWrapper()
        self.user = user
        self.pdu_holder = PduHolder(None)
        self._params = DestFieldWrapper()
        self._crc_helper: Crc32Helper = Crc32Helper(
            ChecksumType.NULL_CHECKSUM, user.vfs
        )

    def __transaction_start_metadata_pdu_to_params(self, metadata_pdu: MetadataPdu):
        self._params.reset()
        self.states.transaction = TransactionStep.TRANSACTION_START
        if metadata_pdu.pdu_header.trans_mode == TransmissionMode.UNACKNOWLEDGED:
            self.states.state = CfdpStates.BUSY_CLASS_1_NACKED
        elif metadata_pdu.pdu_header.trans_mode == TransmissionMode.ACKNOWLEDGED:
            self.states.state = CfdpStates.BUSY_CLASS_2_ACKED
        self._crc_helper.checksum_type = metadata_pdu.checksum_type
        self._closure_requested = metadata_pdu.closure_requested
        if metadata_pdu.dest_file_name is None:
            self._params.fp.no_file_data = True
        else:
            self._params.fp.file_name = Path(metadata_pdu.dest_file_name)
        self._params.fp.size_from_metadata = metadata_pdu.file_size
        self._params.pdu_conf = metadata_pdu.pdu_conf
        self._params.pdu_conf.direction = Direction.TOWARDS_SENDER
        self._params.transaction_id = TransactionId(
            source_entity_id=metadata_pdu.source_entity_id,
            transaction_seq_num=metadata_pdu.transaction_seq_num,
        )
        self.states.transaction_id = self._params.transaction_id
        self._params.remote_cfg = self.remote_cfg_table.get_cfg(
            metadata_pdu.source_entity_id
        )

    def __transaction_start_vfs_handling(self):
        try:
            if self.user.vfs.file_exists(self._params.fp.file_name):
                self.user.vfs.truncate_file(self._params.fp.file_name)
            else:
                self.user.vfs.create_file(self._params.fp.file_name)
        except PermissionError:
            self._params.file_status = FileDeliveryStatus.DISCARDED_FILESTORE_REJECTION
            fh = self.cfg.default_fault_handlers.get_fault_handler(
                ConditionCode.FILESTORE_REJECTION
            )
            if fh == FaultHandlerCode.IGNORE_ERROR:
                pass
            elif fh == FaultHandlerCode.ABANDON_TRANSACTION:
                # TODO: Implement
                pass
            elif fh == FaultHandlerCode.NOTICE_OF_SUSPENSION:
                # TODO: Implement
                pass
            elif fh == FaultHandlerCode.NOTICE_OF_CANCELLATION:
                # TODO: Implement
                pass
            self.cfg.default_fault_handlers.report_fault(
                ConditionCode.FILESTORE_REJECTION
            )

    def _start_transaction(self, metadata_pdu: MetadataPdu) -> bool:
        if self.states.state != CfdpStates.IDLE:
            return False
        self.__transaction_start_metadata_pdu_to_params(metadata_pdu)
        # I am not fully sure whether a remote configuration is strictly required for
        # a destination handler. I think to be fully standard-compliant or at least allow
        # the flexibility to be standard-compliant in the future, we should require that
        # a remote entity configuration exists for each CFDP sender.
        if self._params.remote_cfg is None:
            _LOGGER.warning(
                f"No remote configuration found for remote ID {metadata_pdu.dest_entity_id}"
            )
            raise NoRemoteEntityCfgFound(metadata_pdu.dest_entity_id)
        self.states.transaction = TransactionStep.RECEIVING_FILE_DATA
        self.__transaction_start_vfs_handling()
        msgs_to_user_list = None
        if metadata_pdu.options is not None:
            msgs_to_user_list = []
            for tlv in metadata_pdu.options:
                if tlv.tlv_type == TlvType.MESSAGE_TO_USER:
                    msgs_to_user_list.append(tlv)
        params = MetadataRecvParams(
            transaction_id=self._params.transaction_id,
            file_size=metadata_pdu.file_size,
            source_id=metadata_pdu.source_entity_id,
            dest_file_name=metadata_pdu.dest_file_name,
            source_file_name=metadata_pdu.source_file_name,
            msgs_to_user=msgs_to_user_list,
        )
        self.user.metadata_recv_indication(params)
        return True

    def __idle_fsm(self):
        clear_all_other_pdus = True
        for pdu_type, pdu_deque in self._params.file_directives_dict.items():
            if pdu_type == DirectiveType.METADATA_PDU:
                clear_metadata_deque = False
                for pdu_base in pdu_deque:
                    metadata_pdu = PduHolder(pdu_base).to_metadata_pdu()
                    self._start_transaction(metadata_pdu)
                    # CFDP 4.6.1.2.4: Any repeated metadata should be discarded.
                    if self.states.state != CfdpStates.IDLE:
                        clear_metadata_deque = True
                        break
                if clear_metadata_deque:
                    pdu_deque.clear()
            else:
                # For unacknowledged transfers, there is no lost metadata detection in place.
                # For now, simply discard all PDUs which arrive before the Metadata PDU.
                # TODO: This is tricky for acknowledged mode. This implementation writes to the
                #       virtual filestore directly. If lost segment detection is in place, all
                #       PDUs which arrive successfully after a missing metadata PDU would have
                #       to be counted as lost segments.
                # clear_all_other_pdus = False
                pass
        if self.states.state == CfdpStates.IDLE and clear_all_other_pdus:
            if self._params.file_directives_dict:
                for other_pdu in self._params.file_directives_dict:
                    _LOGGER.warning(
                        f"Received {other_pdu} PDU without "
                        f"first receiving metadata PDU first. Discarding it"
                    )
                self._params.file_directives_dict.clear()
            if self._params.file_data_deque:
                _LOGGER.warning(
                    f"Received {len(self._params.file_data_deque)} file data PDUs without "
                    f"first receiving metadata PDU first. Discarding them"
                )
                self._params.file_data_deque.clear()

    def __busy_naked_fsm(self):
        if self.states.transaction == TransactionStep.RECEIVING_FILE_DATA:
            self.__receiving_fd_pdus_nacknowledged()
        if self.states.transaction == TransactionStep.TRANSFER_COMPLETION:
            self._handle_transfer_completion()
        if self.states.transaction == TransactionStep.SENDING_FINISHED_PDU:
            self._prepare_finished_pdu()
            self.states.packet_ready = True

    def __receiving_fd_pdus_nacknowledged(self):
        # TODO: Sequence count check
        for file_data_pdu in self._params.file_data_deque:
            self.__handle_one_fd_pdu(file_data_pdu)
        # TODO: Support for check timer missing
        eof_pdus = self._params.file_directives_dict.get(DirectiveType.EOF_PDU)
        if eof_pdus is not None:
            for pdu in eof_pdus:
                eof_pdu = PduHolder(pdu).to_eof_pdu()
                self._handle_eof_pdu(eof_pdu)

    def __handle_one_fd_pdu(self, file_data_pdu: FileDataPdu):
        data = file_data_pdu.file_data
        offset = file_data_pdu.offset
        if self.cfg.indication_cfg.file_segment_recvd_indication_required:
            file_segment_indic_params = FileSegmentRecvdParams(
                transaction_id=self._params.transaction_id,
                length=len(file_data_pdu.file_data),
                offset=offset,
                record_cont_state=file_data_pdu.record_cont_state,
                segment_metadata=file_data_pdu.segment_metadata,
            )
            self.user.file_segment_recv_indication(file_segment_indic_params)
        try:
            self.user.vfs.write_data(self._params.fp.file_name, data, offset)
            self._params.file_status = FileDeliveryStatus.FILE_RETAINED
            # Ensure that the progress value is always incremented
            if offset + len(file_data_pdu.file_data) > self._params.fp.progress:
                self._params.fp.progress = offset + len(file_data_pdu.file_data)
        except FileNotFoundError:
            if self._params.file_status != FileDeliveryStatus.FILE_RETAINED:
                self._params.file_status = FileDeliveryStatus.DISCARDED_DELIBERATELY
        except PermissionError:
            if self._params.file_status != FileDeliveryStatus.FILE_RETAINED:
                self._params.file_status = (
                    FileDeliveryStatus.DISCARDED_FILESTORE_REJECTION
                )

    def state_machine(self) -> FsmResult:
        if self.states.state == CfdpStates.IDLE:
            self.__idle_fsm()
        if self.states.state == CfdpStates.BUSY_CLASS_1_NACKED:
            self.__busy_naked_fsm()
        return FsmResult(self.states, self.pdu_holder)

    def finish(self):
        self._params.reset()
        # Not fully sure this is the best approach, but I think this is ok for now
        self._params.clear_file_directive_dict()
        self._params.clear_file_deque()
        self._params.transaction_id = None
        self.states.state = CfdpStates.IDLE
        self.states.transaction = TransactionStep.IDLE

    def pass_packet(self, packet: GenericPduPacket):
        # TODO: Sanity checks
        if packet.pdu_type == PduType.FILE_DATA:
            self._params.file_data_deque.append(cast(FileDataPdu, packet))
        else:
            if packet.directive_type in self._params.file_directives_dict:
                self._params.file_directives_dict.get(packet.directive_type).append(
                    packet
                )
            else:
                self._params.file_directives_dict.update(
                    {packet.directive_type: [packet]}
                )

    def confirm_packet_sent_advance_fsm(self):
        """Helper method which performs both :py:meth:`confirm_packet_sent` and
        :py:meth:`advance_fsm`
        """
        self.confirm_packet_sent()
        self.advance_fsm()

    def confirm_packet_sent(self):
        """Confirm that a packet generated by the :py:meth:`operation` was sent successfully"""
        self.states.packet_ready = False

    def advance_fsm(self):
        if self.states.packet_ready:
            raise PacketSendNotConfirmed(
                f"Must send current packet {self.pdu_holder.base} first"
            )
        if self.states.transaction == TransactionStep.SENDING_FINISHED_PDU:
            self.finish()

    def _handle_transfer_completion(self):
        if self._crc_helper.checksum_type != ChecksumType.NULL_CHECKSUM:
            self._checksum_verify()
        elif (
            self._params.fp.no_file_data
            or self._crc_helper.checksum_type == ChecksumType.NULL_CHECKSUM
        ):
            self._params.condition_code = ConditionCode.NO_ERROR
        self._notice_of_completion()
        if self.states.state == CfdpStates.BUSY_CLASS_1_NACKED:
            if self._params.closure_requested:
                self.states.transaction = TransactionStep.SENDING_FINISHED_PDU
            else:
                self.finish()
        elif self.states.state == CfdpStates.BUSY_CLASS_2_ACKED:
            self.states.transaction = TransactionStep.SENDING_FINISHED_PDU

    def _handle_eof_pdu(self, eof_pdu: EofPdu):
        # TODO: Error handling
        if eof_pdu.condition_code == ConditionCode.NO_ERROR:
            self._params.fp.crc32 = eof_pdu.file_checksum
            file_size_from_eof = eof_pdu.file_size
            # CFDP 4.6.1.2.9: Declare file size error if progress exceeds file size
            if self._params.fp.progress > file_size_from_eof:
                # TODO: File Size error
                pass
            self._params.fp.file_size = file_size_from_eof
            self._params.fp.segment_len = self._params.remote_cfg.max_file_segment_len
            if self.cfg.indication_cfg.eof_recv_indication_required:
                self.user.eof_recv_indication(self._params.transaction_id)
            if self.states.transaction == TransactionStep.RECEIVING_FILE_DATA:
                if self.states.state == CfdpStates.BUSY_CLASS_1_NACKED:
                    self.states.transaction = TransactionStep.TRANSFER_COMPLETION
                elif self.states.state == CfdpStates.BUSY_CLASS_2_ACKED:
                    self.states.transaction = TransactionStep.SENDING_ACK_PDU

    def _checksum_verify(self):
        crc32 = self._crc_helper.calc_for_file(
            self._params.fp.file_name,
            self._params.fp.file_size,
            self._params.fp.segment_len,
        )
        if crc32 != self._params.fp.crc32:
            # TODO: CFDP Checksum error handling
            self._params.condition_code = ConditionCode.FILE_CHECKSUM_FAILURE
        else:
            self._params.delivery_code = DeliveryCode.DATA_COMPLETE
            self._params.condition_code = ConditionCode.NO_ERROR

    def _notice_of_completion(self):
        if self.cfg.indication_cfg.transaction_finished_indication_required:
            finished_indic_params = TransactionFinishedParams(
                transaction_id=self._params.transaction_id,
                condition_code=self._params.condition_code,
                delivery_code=self._params.delivery_code,
                file_status=self._params.file_status,
                status_report=None,
            )
            self.user.transaction_finished_indication(finished_indic_params)

    def _prepare_finished_pdu(self):
        if self.states.packet_ready:
            raise PacketSendNotConfirmed(
                f"Must send current packet {self.pdu_holder.base} first"
            )
        finished_params = FinishedParams(
            condition_code=self._params.condition_code,
            # TODO: Find out how those are used
            delivery_code=DeliveryCode.DATA_COMPLETE,
            delivery_status=FileDeliveryStatus.FILE_RETAINED,
        )
        finished_pdu = FinishedPdu(
            params=finished_params,
            # The configuration was cached when the first metadata arrived
            pdu_conf=self._params.pdu_conf,
        )
        self.pdu_holder.base = finished_pdu
