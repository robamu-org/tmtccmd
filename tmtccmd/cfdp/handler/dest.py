from __future__ import annotations

import dataclasses
import enum
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import deprecation

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
from tmtccmd.cfdp.defs import CfdpState, TransactionId
from tmtccmd.cfdp.handler.common import PacketDestination, get_packet_destination
from tmtccmd.cfdp.handler.crc import Crc32Helper
from tmtccmd.cfdp.handler.defs import (
    FileParamsBase,
    FsmNotCalledAfterPacketInsertion,
    InvalidDestinationId,
    InvalidPduDirection,
    UnretrievedPdusToBeSent,
    NoRemoteEntityCfgFound,
)
from tmtccmd.cfdp.user import (
    MetadataRecvParams,
    FileSegmentRecvdParams,
    TransactionFinishedParams,
)
from tmtccmd.version import get_version

_LOGGER = logging.getLogger(__name__)


class InvalidPduForDestHandler(Exception):
    def __init__(self, packet: GenericPduPacket):
        self.packet = packet
        super().__init__(f"Invalid packet {self.packet} for source handler")


class PduIgnoredReason(enum.IntEnum):
    # First packet received was not a metadata PDU.
    FIRST_PACKET_NOT_METADATA_PDU = 0
    # The received PDU can only be handled in acknowledged mode.
    ACK_MODE_PACKET_INVALID_MODE = 1


class PduIgnoredForDest(Exception):
    def __init__(self, reason: PduIgnoredReason, ignored_packet: GenericPduPacket):
        self.ignored_packet = ignored_packet
        self.reason = reason
        super().__init__(f"ignored PDU packet at destination handler: {reason!r}")


@dataclass
class _DestFileParams(FileParamsBase):
    file_name: Path
    file_size_eof: Optional[int]

    @classmethod
    def empty(cls) -> _DestFileParams:
        return cls(
            progress=0,
            segment_len=0,
            crc32=bytes(),
            file_size=0,
            file_name=Path(),
            file_size_eof=None,
            no_file_data=False,
        )

    def reset(self):
        super().reset()
        self.file_name = Path()
        self.file_size_eof = None


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
    state: CfdpState = CfdpState.IDLE
    transaction: TransactionStep = TransactionStep.IDLE
    transaction_id: Optional[TransactionId] = None
    packet_ready: bool = False


@dataclass
class _DestFieldWrapper:
    """Private wrapper class for internal use only."""

    transaction_id: Optional[TransactionId] = None
    remote_cfg: Optional[RemoteEntityCfg] = None
    closure_requested: bool = False
    condition_code: ConditionCode = ConditionCode.NO_CONDITION_FIELD
    delivery_code: DeliveryCode = DeliveryCode.DATA_INCOMPLETE
    file_status: FileDeliveryStatus = FileDeliveryStatus.DISCARDED_DELIBERATELY
    pdu_conf: PduConfig = dataclasses.field(default_factory=lambda: PduConfig.empty())
    fp: _DestFileParams = dataclasses.field(
        default_factory=lambda: _DestFileParams.empty()
    )
    last_inserted_packet = PduHolder(None)

    def reset(self):
        self.transaction_id = None
        self.closure_requested = False
        self.condition_code = ConditionCode.NO_CONDITION_FIELD
        self.delivery_code = DeliveryCode.DATA_INCOMPLETE
        self.pdu_conf = PduConfig.empty()
        self.fp.reset()
        self.remote_cfg = None
        self.last_inserted_packet.pdu = None


class FsmResult:
    def __init__(self, states: DestStateWrapper, pdu_holder: PduHolder):
        self.states = states
        self.pdu_holder = pdu_holder


class DestHandler:
    """This is the primary CFDP destination handler. It models the CFDP source entity, which is
    primarily responsible for receiving files sent from another CFDP entity. It performs the
    reception side of File Copy Operations.
    The following core functions are the primary interface for a direct usage or for a composite
    handler with a source handler and a destination handler as member objects:

     1. :py:meth:`insert_packet` : Can be used to insert packets into the destination
        handler. Please note that the destination handler can also only process Metadata, EOF and
        Prompt PDUs in addition to ACK PDUs where the acknowledged PDU is the Finished PDU.
        Right now, the handler processes one packet at a time, and each packer insertion needs
        to be followed by a :py:meth:`state_machine` call.
     2. :py:meth:`state_machine` : This state machine processes inserted packets while also
        generating the packets which need to be sent back to the initiator of a file copy
        operation.
     3. :py:meth:`confirm_packet_sent_advance_fsm` : Confirm that the PDUs generated by the last
        state machine iteration was sent successfully and advance the state machine.
    """

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
        self._params = _DestFieldWrapper()
        self._crc_helper: Crc32Helper = Crc32Helper(
            ChecksumType.NULL_CHECKSUM, user.vfs
        )

    """This is the primary call to run the state machine after packet insertion and/or after
    having sent any packets which need to be sent to the sender of a file transaction."""

    def state_machine(self) -> FsmResult:
        if self.states.state == CfdpState.IDLE:
            self.__idle_fsm()
        if self.states.state == CfdpState.BUSY_CLASS_1_NACKED:
            self.__busy_naked_fsm()
        return FsmResult(self.states, self.pdu_holder)

    def closure_requested(self) -> bool:
        """Returns whether a closure was requested for the current transaction. Please note that
        this variable is only valid as long as the state is not IDLE"""
        return self._params.closure_requested

    def finish(self):
        self._params.reset()
        # Not fully sure this is the best approach, but I think this is ok for now
        self._params.transaction_id = None
        self.states.state = CfdpState.IDLE
        self.states.transaction = TransactionStep.IDLE

    def insert_packet(self, packet: GenericPduPacket):
        """Insert a packet into the state machine. The packet will be processed with the
        next :py:meth:`state_machine` call, which might lead to state machine transitions
        and/or new packets generated, which need to be sent to the file sender for the
        corresponding file transaction.

        :raise NoRemoteEntityCfgFound: No remote configuration found for source entity ID
            extracted from the PDU packet.
        :raise FsmNotCalledAfterPacketInsertion: :py:meth:`state_machine` needs to be called
            to clear a previously inserted packet.
        :raise InvalidPduDirection: PDU direction bit is invalid.
        :raise InvalidDestinationId: The PDU destination entity ID is not equal to the configured
            local ID.
        :raise InvalidPduForDestHandler: The PDU type can not be handled by the destination handler
        :raise PduIgnoredForDest: The PDU was ignored because it can not be handled for the current
            transmission mode or internal state.
        """
        if self._params.last_inserted_packet.pdu is not None:
            raise FsmNotCalledAfterPacketInsertion()
        if packet.direction != Direction.TOWARDS_RECEIVER:
            raise InvalidPduDirection(
                Direction.TOWARDS_RECEIVER, packet.pdu_header.direction
            )
        if packet.dest_entity_id != self.cfg.local_entity_id:
            raise InvalidDestinationId(
                self.cfg.local_entity_id, packet.source_entity_id
            )
        # TODO: This can happen if a packet is received for which no transaction was started..
        #       A better exception might be worth a thought..
        if self.remote_cfg_table.get_cfg(packet.source_entity_id) is None:
            raise NoRemoteEntityCfgFound(entity_id=packet.dest_entity_id)
        if get_packet_destination(packet) == PacketDestination.SOURCE_HANDLER:
            raise InvalidPduForDestHandler(packet)
        if self.states.state == CfdpState.IDLE and (
            packet.pdu_type == PduType.FILE_DATA
            or packet.directive_type != DirectiveType.METADATA_PDU  # type: ignore
        ):
            raise PduIgnoredForDest(
                PduIgnoredReason.FIRST_PACKET_NOT_METADATA_PDU, packet
            )
        if packet.pdu_type == PduType.FILE_DIRECTIVE and (
            packet.directive_type  # type: ignore
            in [DirectiveType.ACK_PDU, DirectiveType.PROMPT_PDU]
            and self.states.state == CfdpState.BUSY_CLASS_1_NACKED
        ):
            raise PduIgnoredForDest(
                PduIgnoredReason.ACK_MODE_PACKET_INVALID_MODE, packet
            )
        self._params.last_inserted_packet.pdu = packet

    def confirm_packet_sent_advance_fsm(self):
        """Helper method which performs both :py:meth:`confirm_packet_sent` and
        :py:meth:`advance_fsm`
        """
        self.confirm_packet_sent()
        self.advance_fsm()

    def advance_fsm(self):
        if self.states.packet_ready:
            raise UnretrievedPdusToBeSent()
        if self.states.transaction == TransactionStep.SENDING_FINISHED_PDU:
            self.finish()

    def confirm_packet_sent(self):
        """Confirm that a packet generated by the :py:meth:`operation` was sent successfully"""
        self.states.packet_ready = False

    def __transaction_start_metadata_pdu_to_params(self, metadata_pdu: MetadataPdu):
        self._params.reset()
        self.states.transaction = TransactionStep.TRANSACTION_START
        if metadata_pdu.pdu_header.trans_mode == TransmissionMode.UNACKNOWLEDGED:
            self.states.state = CfdpState.BUSY_CLASS_1_NACKED
        elif metadata_pdu.pdu_header.trans_mode == TransmissionMode.ACKNOWLEDGED:
            self.states.state = CfdpState.BUSY_CLASS_2_ACKED
        self._crc_helper.checksum_type = metadata_pdu.checksum_type
        self._params.closure_requested = metadata_pdu.closure_requested
        if metadata_pdu.dest_file_name is None:
            self._params.fp.no_file_data = True
        else:
            self._params.fp.file_name = Path(metadata_pdu.dest_file_name)
        self._params.fp.file_size = metadata_pdu.file_size
        self._params.pdu_conf = metadata_pdu.pdu_header.pdu_conf
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
        if self.states.state != CfdpState.IDLE:
            return False
        self.__transaction_start_metadata_pdu_to_params(metadata_pdu)
        # I am not fully sure whether a remote configuration is strictly required for
        # a destination handler. I think to be fully standard-compliant or at least allow
        # the flexibility to be standard-compliant in the future, we should require that
        # a remote entity configuration exists for each CFDP sender.
        if self._params.remote_cfg is None:
            _LOGGER.warning(
                "No remote configuration found for remote ID"
                f" {metadata_pdu.dest_entity_id}"
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
            transaction_id=self._params.transaction_id,  # type: ignore
            file_size=metadata_pdu.file_size,
            source_id=metadata_pdu.source_entity_id,
            dest_file_name=metadata_pdu.dest_file_name,
            source_file_name=metadata_pdu.source_file_name,
            msgs_to_user=msgs_to_user_list,
        )
        self.user.metadata_recv_indication(params)
        return True

    def __idle_fsm(self):
        if self._params.last_inserted_packet.pdu is None:
            return
        if (
            self._params.last_inserted_packet.pdu.directive_type  # type: ignore
            == DirectiveType.METADATA_PDU
        ):
            metadata_pdu = self._params.last_inserted_packet.to_metadata_pdu()
            self._start_transaction(metadata_pdu)
        else:
            self._params.last_inserted_packet.pdu = None
            raise ValueError(
                f"unexpected configuration error: {self._params.last_inserted_packet.pdu} in "
                f"IDLE state machine"
            )

    def __busy_naked_fsm(self):
        if self.states.transaction == TransactionStep.RECEIVING_FILE_DATA:
            self.__receiving_fd_pdus_nacknowledged()
        if self.states.transaction == TransactionStep.TRANSFER_COMPLETION:
            self._handle_transfer_completion()
        if self.states.transaction == TransactionStep.SENDING_FINISHED_PDU:
            self._prepare_finished_pdu()
            self.states.packet_ready = True

    def __receiving_fd_pdus_nacknowledged(self):
        if self._params.last_inserted_packet.pdu is None:
            return
        if self._params.last_inserted_packet.pdu.pdu_type == PduType.FILE_DATA:
            self.__handle_one_fd_pdu(
                self._params.last_inserted_packet.to_file_data_pdu()
            )
        elif (
            self._params.last_inserted_packet.pdu.directive_type  # type: ignore
            == DirectiveType.EOF_PDU
        ):
            self._handle_eof_pdu(self._params.last_inserted_packet.to_eof_pdu())
        self._params.last_inserted_packet.pdu = None

    def __handle_one_fd_pdu(self, file_data_pdu: FileDataPdu):
        data = file_data_pdu.file_data
        offset = file_data_pdu.offset
        if self.cfg.indication_cfg.file_segment_recvd_indication_required:
            file_segment_indic_params = FileSegmentRecvdParams(
                transaction_id=self._params.transaction_id,  # type: ignore
                length=len(file_data_pdu.file_data),
                offset=offset,
                record_cont_state=file_data_pdu.record_cont_state,
                segment_metadata=file_data_pdu.segment_metadata,
            )
            self.user.file_segment_recv_indication(file_segment_indic_params)
        try:
            self.user.vfs.write_data(self._params.fp.file_name, data, offset)
            self._params.file_status = FileDeliveryStatus.FILE_RETAINED

            if self._params.fp.file_size_eof is not None and (
                offset + len(file_data_pdu.file_data) > self._params.fp.file_size_eof
            ):
                # CFDP 4.6.1.2.7 c): If the sum of the FD PDU offset and segment size exceeds
                # the file size indicated in the first previously received EOF (No Error) PDU, if
                # any, then then a File Size Errorfaul shall be declared.
                # TODO: Declare File Size error instead of exception.
                raise ValueError("CFDP File Size Error")
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

    @deprecation.deprecated(
        deprecated_in="6.0.0rc1",
        current_version=get_version(),
        details="Use insert_packet instead",
    )
    def pass_packet(self, packet: GenericPduPacket):
        self.insert_packet(packet)

    def _handle_transfer_completion(self):
        if self._crc_helper.checksum_type != ChecksumType.NULL_CHECKSUM:
            self._checksum_verify()
        elif (
            self._params.fp.no_file_data
            or self._crc_helper.checksum_type == ChecksumType.NULL_CHECKSUM
        ):
            self._params.condition_code = ConditionCode.NO_ERROR
        self._notice_of_completion()
        if self.states.state == CfdpState.BUSY_CLASS_1_NACKED:
            if self._params.closure_requested:
                self.states.transaction = TransactionStep.SENDING_FINISHED_PDU
            else:
                self.finish()
        elif self.states.state == CfdpState.BUSY_CLASS_2_ACKED:
            self.states.transaction = TransactionStep.SENDING_FINISHED_PDU

    def _handle_eof_pdu(self, eof_pdu: EofPdu):
        # TODO: Error handling, cancel request handling.
        if eof_pdu.condition_code == ConditionCode.NO_ERROR:
            self._params.fp.crc32 = eof_pdu.file_checksum
            self._params.fp.file_size_eof = eof_pdu.file_size
            # CFDP 4.6.1.2.9: Declare file size error if progress exceeds file size
            if self._params.fp.progress > self._params.fp.file_size_eof:
                # TODO: File Size error
                raise ValueError("CFDP File Size Error")
            if self._params.fp.file_size_eof != self._params.fp.file_size:
                # Can or should this ever happen for a No Error EOF? Treat this like a non-fatal
                # error for now..
                _LOGGER.warn(
                    "missmatch of EOF file size and Metadata File Size for success EOF"
                )
            if self.cfg.indication_cfg.eof_recv_indication_required:
                self.user.eof_recv_indication(self._params.transaction_id)  # type: ignore
            if self.states.transaction == TransactionStep.RECEIVING_FILE_DATA:  # type: ignore
                if self.states.state == CfdpState.BUSY_CLASS_1_NACKED:
                    self.states.transaction = TransactionStep.TRANSFER_COMPLETION
                elif self.states.state == CfdpState.BUSY_CLASS_2_ACKED:
                    self.states.transaction = TransactionStep.SENDING_ACK_PDU

    def _checksum_verify(self):
        crc32 = self._crc_helper.calc_for_file(
            self._params.fp.file_name, self._params.fp.file_size
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
                transaction_id=self._params.transaction_id,  # type: ignore
                condition_code=self._params.condition_code,
                delivery_code=self._params.delivery_code,
                file_status=self._params.file_status,
                status_report=None,
            )
            self.user.transaction_finished_indication(finished_indic_params)

    def _prepare_finished_pdu(self):
        if self.states.packet_ready:
            raise UnretrievedPdusToBeSent()
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
        self.pdu_holder.pdu = finished_pdu
