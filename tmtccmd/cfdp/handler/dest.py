from __future__ import annotations
from collections import deque

import dataclasses
import enum
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Deque, Optional

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
from tmtccmd.cfdp.mib import CheckTimerProvider, EntityType
from tmtccmd.util.countdown import Countdown
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


class CompletionDisposition(enum.Enum):
    COMPLETED = 0
    CANCELED = 1


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
    TRANSACTION_START = 1
    """Metadata was received, which triggered a transaction start."""
    RECEIVING_FILE_DATA = 2
    WAITING_FOR_CHECK_TIMER = 3
    """This is the check timer step as specified in chapter 4.6.3.3 b) of the standard."""
    SENDING_EOF_ACK_PDU = 4
    """Sending the ACK (EOF) packet."""
    TRANSFER_COMPLETION = 5
    """File transfer complete. Perform checksum verification and notice of completion. Please
    note that this does not necessarily mean that the file transfer was completed succesfully."""
    SENDING_FINISHED_PDU = 6
    WAITING_FOR_FINISHED_ACK = 7


@dataclass
class DestStateWrapper:
    state: CfdpState = CfdpState.IDLE
    step: TransactionStep = TransactionStep.IDLE
    transaction_id: Optional[TransactionId] = None
    packets_ready: bool = False


@dataclass
class _DestFieldWrapper:
    """Private wrapper class for internal use only."""

    transaction_id: Optional[TransactionId] = None
    remote_cfg: Optional[RemoteEntityCfg] = None
    check_timer: Optional[Countdown] = None
    current_check_count: int = 0
    closure_requested: bool = False
    finished_params: FinishedParams = FinishedParams.empty()
    completion_disposition: CompletionDisposition = CompletionDisposition.COMPLETED
    pdu_conf: PduConfig = dataclasses.field(default_factory=lambda: PduConfig.empty())
    fp: _DestFileParams = dataclasses.field(
        default_factory=lambda: _DestFileParams.empty()
    )
    last_inserted_packet = PduHolder(None)

    def reset(self):
        self.transaction_id = None
        self.closure_requested = False
        self.pdu_conf = PduConfig.empty()
        self.finished_params = FinishedParams.empty()
        self.finished_params.delivery_status = FileDeliveryStatus.FILE_STATUS_UNREPORTED
        self.completion_disposition = CompletionDisposition.COMPLETED
        self.fp.reset()
        self.remote_cfg = None
        self.last_inserted_packet.pdu = None


class FsmResult:
    def __init__(self, states: DestStateWrapper):
        self.states = states


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
     3. :py:meth:`get_next_packet`: Retrieve next packet to be sent back to the remote CFDP source
        entity ID.

    A new file transfer (Metadata PDU reception) is only be accepted if the handler is in the IDLE
    state. Furthermore, packet insertion is not allowed until all packets to send were retrieved
    after a state machine call."""

    def __init__(
        self,
        cfg: LocalEntityCfg,
        user: CfdpUserBase,
        remote_cfg_table: RemoteEntityCfgTable,
        check_timer_provider: CheckTimerProvider,
    ):
        self.cfg = cfg
        self.remote_cfg_table = remote_cfg_table
        self.states = DestStateWrapper()
        self.user = user
        self.check_timer_provider = check_timer_provider
        self._params = _DestFieldWrapper()
        self._cksum_verif_helper: Crc32Helper = Crc32Helper(
            ChecksumType.NULL_CHECKSUM, user.vfs
        )
        self._pdus_to_be_sent: Deque[PduHolder] = deque()

    def state_machine(self) -> FsmResult:
        """This is the primary call to run the state machine after packet insertion and/or after
        having sent any packets which need to be sent to the sender of a file transaction."""
        if self.states.state == CfdpState.IDLE:
            self.__idle_fsm()
        else:
            self.__non_idle_fsm()
        return FsmResult(self.states)

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

    def get_next_packet(self) -> Optional[PduHolder]:
        """Retrieve the next packet which should be sent to the remote CFDP source entity."""
        if len(self._pdus_to_be_sent) <= 1:
            self.states.packets_ready = False
        if len(self._pdus_to_be_sent) == 0:
            return None
        return self._pdus_to_be_sent.popleft()

    def closure_requested(self) -> bool:
        """Returns whether a closure was requested for the current transaction. Please note that
        this variable is only valid as long as the state is not IDLE"""
        return self._params.closure_requested

    @property
    def packets_ready(self) -> bool:
        return self.states.packets_ready

    def reset(self):
        """This function is public to allow completely resetting the handler, but it is explicitely
        discouraged to do this. CFDP generally has mechanism to detect issues and errors on itself.
        """
        self._params.reset()
        # Not fully sure this is the best approach, but I think this is ok for now
        self._params.transaction_id = None
        self._pdus_to_be_sent.clear()
        self.states.state = CfdpState.IDLE
        self.states.step = TransactionStep.IDLE

    def _fsm_advancement_after_packets_were_sent(self):
        """Advance the internal FSM after all packets to be sent were retrieved from the handler."""
        if len(self._pdus_to_be_sent) > 0:
            raise UnretrievedPdusToBeSent(
                f"{len(self._pdus_to_be_sent)} packets left to send"
            )
        if self.states.step == TransactionStep.SENDING_FINISHED_PDU:
            self.reset()

    def __transaction_start_metadata_pdu_to_params(self, metadata_pdu: MetadataPdu):
        self._params.reset()
        self.states.step = TransactionStep.TRANSACTION_START
        if metadata_pdu.transmission_mode == TransmissionMode.UNACKNOWLEDGED:
            self.states.state = CfdpState.BUSY_CLASS_1_NACKED
        elif metadata_pdu.transmission_mode == TransmissionMode.ACKNOWLEDGED:
            self.states.state = CfdpState.BUSY_CLASS_2_ACKED
        self._cksum_verif_helper.checksum_type = metadata_pdu.checksum_type
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
            self._params.finished_params.delivery_status = (
                FileDeliveryStatus.FILE_RETAINED
            )
        except PermissionError:
            self._params.finished_params.delivery_status = (
                FileDeliveryStatus.DISCARDED_FILESTORE_REJECTION
            )
            self._declare_fault(ConditionCode.FILESTORE_REJECTION)

    def _start_transaction(self, metadata_pdu: MetadataPdu) -> bool:
        if self.states.state != CfdpState.IDLE:
            return False
        self.__transaction_start_metadata_pdu_to_params(metadata_pdu)
        # To be fully standard-compliant or at least allow the flexibility to be standard-compliant
        # in the future, we should require that a remote entity configuration exists for each CFDP
        # sender.
        if self._params.remote_cfg is None:
            _LOGGER.warning(
                "No remote configuration found for remote ID"
                f" {metadata_pdu.dest_entity_id}"
            )
            raise NoRemoteEntityCfgFound(metadata_pdu.dest_entity_id)
        self.states.step = TransactionStep.RECEIVING_FILE_DATA
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

    def __non_idle_fsm(self):
        self._fsm_advancement_after_packets_were_sent()
        if self.states.step == TransactionStep.RECEIVING_FILE_DATA:
            self.__receiving_fd_and_eof_pdus()
        if self.states.step == TransactionStep.TRANSFER_COMPLETION:
            self._handle_transfer_completion()
        if self.states.step == TransactionStep.SENDING_FINISHED_PDU:
            self._prepare_finished_pdu()
        if self.states.step == TransactionStep.WAITING_FOR_CHECK_TIMER:
            self._check_limit_handling()

    def __receiving_fd_and_eof_pdus(self):
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
                segment_metadata=file_data_pdu.segment_metadata,
            )
            self.user.file_segment_recv_indication(file_segment_indic_params)
        try:
            self.user.vfs.write_data(self._params.fp.file_name, data, offset)
            self._params.finished_params.delivery_status = (
                FileDeliveryStatus.FILE_RETAINED
            )

            if self._params.fp.file_size_eof is not None and (
                offset + len(file_data_pdu.file_data) > self._params.fp.file_size_eof
            ):
                # CFDP 4.6.1.2.7 c): If the sum of the FD PDU offset and segment size exceeds
                # the file size indicated in the first previously received EOF (No Error) PDU, if
                # any, then then a File Size Error fault shall be declared.
                if (
                    self._declare_fault(ConditionCode.FILE_SIZE_ERROR)
                    != FaultHandlerCode.IGNORE_ERROR
                ):
                    return
            # Ensure that the progress value is always incremented
            if offset + len(file_data_pdu.file_data) > self._params.fp.progress:
                self._params.fp.progress = offset + len(file_data_pdu.file_data)
        except FileNotFoundError:
            if (
                self._params.finished_params.delivery_status
                != FileDeliveryStatus.FILE_RETAINED
            ):
                self._params.finished_params.delivery_status = (
                    FileDeliveryStatus.DISCARDED_FILESTORE_REJECTION
                )
                self._declare_fault(ConditionCode.FILESTORE_REJECTION)
        except PermissionError:
            if (
                self._params.finished_params.delivery_status
                != FileDeliveryStatus.FILE_RETAINED
            ):
                self._params.finished_params.delivery_status = (
                    FileDeliveryStatus.DISCARDED_FILESTORE_REJECTION
                )
                self._declare_fault(ConditionCode.FILESTORE_REJECTION)

    @deprecation.deprecated(
        deprecated_in="6.0.0rc1",
        current_version=get_version(),
        details="Use insert_packet instead",
    )
    def pass_packet(self, packet: GenericPduPacket):
        self.insert_packet(packet)

    def _handle_transfer_completion(self):
        if self._cksum_verif_helper.checksum_type != ChecksumType.NULL_CHECKSUM:
            self._checksum_verify()
        elif (
            self._params.fp.no_file_data
            or self._cksum_verif_helper.checksum_type == ChecksumType.NULL_CHECKSUM
        ):
            self._params.finished_params.condition_code = ConditionCode.NO_ERROR
        self._notice_of_completion()
        if self.states.state == CfdpState.BUSY_CLASS_1_NACKED:
            if self._params.closure_requested:
                self.states.step = TransactionStep.SENDING_FINISHED_PDU
            else:
                self.reset()
        elif self.states.state == CfdpState.BUSY_CLASS_2_ACKED:
            # TODO: Need to send ACK for the EOF PDU here..
            pass
            # self.states.step = TransactionStep.SENDING_FINISHED_PDU

    def _handle_eof_pdu(self, eof_pdu: EofPdu):
        self._params.fp.crc32 = eof_pdu.file_checksum
        self._params.fp.file_size_eof = eof_pdu.file_size
        if eof_pdu.condition_code == ConditionCode.NO_ERROR:
            # CFDP 4.6.1.2.9: Declare file size error if progress exceeds file size
            if self._params.fp.progress > self._params.fp.file_size_eof:
                if (
                    self._declare_fault(ConditionCode.FILE_SIZE_ERROR)
                    != FaultHandlerCode.IGNORE_ERROR
                ):
                    return
            if self._params.fp.file_size_eof != self._params.fp.file_size:
                # Can or should this ever happen for a No Error EOF? Treat this like a non-fatal
                # error for now..
                _LOGGER.warn(
                    "missmatch of EOF file size and Metadata File Size for success EOF"
                )
            if self.cfg.indication_cfg.eof_recv_indication_required:
                self.user.eof_recv_indication(self._params.transaction_id)  # type: ignore
        else:
            # This is an EOF (Cancel), perform Cancel Response Procedures according to chapter
            # 4.6.6 of the standard.
            self._params.completion_disposition = CompletionDisposition.CANCELED
            self._params.finished_params.condition_code = eof_pdu.condition_code
            # Store this as progress for the checksum calculation.
            self._params.fp.progress = self._params.fp.file_size_eof
            self._params.finished_params.delivery_code = DeliveryCode.DATA_INCOMPLETE
        if self.states.step == TransactionStep.RECEIVING_FILE_DATA:  # type: ignore
            if self.states.state == CfdpState.BUSY_CLASS_1_NACKED:
                self.states.step = TransactionStep.TRANSFER_COMPLETION
            elif self.states.state == CfdpState.BUSY_CLASS_2_ACKED:
                self.states.step = TransactionStep.SENDING_EOF_ACK_PDU

    def _checksum_verify(self):
        # If the transfer was cancelled, I don't really see a point in calculating the checksum..
        # We need to report the reason for the cancellation.
        crc32 = self._cksum_verif_helper.calc_for_file(
            self._params.fp.file_name, self._params.fp.progress
        )
        if crc32 == self._params.fp.crc32:
            self._params.finished_params.delivery_code = DeliveryCode.DATA_COMPLETE
            self._params.finished_params.condition_code = ConditionCode.NO_ERROR
        else:
            self._params.finished_params.condition_code = (
                ConditionCode.FILE_CHECKSUM_FAILURE
            )
            self.states.step = TransactionStep.WAITING_FOR_CHECK_TIMER
            if (
                self._declare_fault(ConditionCode.FILE_CHECKSUM_FAILURE)
                != FaultHandlerCode.IGNORE_ERROR
            ):
                return
            assert self._params.remote_cfg is not None
            self._params.check_timer = self.check_timer_provider.provide_check_timer(
                self.cfg.local_entity_id,
                self._params.remote_cfg.entity_id,
                EntityType.RECEIVING,
            )

    def _notice_of_completion(self):
        if self._params.completion_disposition == CompletionDisposition.COMPLETED:
            # TODO: Execute any filestore requests
            pass
        elif self._params.completion_disposition == CompletionDisposition.CANCELED:
            assert self._params.remote_cfg is not None
            if self._params.remote_cfg.disposition_on_cancellation:
                self.user.vfs.delete_file(self._params.fp.file_name)
                self._params.finished_params.delivery_status = (
                    FileDeliveryStatus.DISCARDED_DELIBERATELY
                )
        if self.cfg.indication_cfg.transaction_finished_indication_required:
            finished_indic_params = TransactionFinishedParams(
                transaction_id=self._params.transaction_id,  # type: ignore
                finished_params=self._params.finished_params,
                status_report=None,
            )
            self.user.transaction_finished_indication(finished_indic_params)

    def _prepare_finished_pdu(self):
        if self.states.packets_ready:
            raise UnretrievedPdusToBeSent()
        finished_pdu = FinishedPdu(
            params=self._params.finished_params,
            # The configuration was cached when the first metadata arrived
            pdu_conf=self._params.pdu_conf,
        )
        self._add_packet_to_be_sent(finished_pdu)

    def _add_packet_to_be_sent(self, packet: GenericPduPacket):
        self._pdus_to_be_sent.append(PduHolder(packet))
        self.states.packets_ready = True

    def _check_limit_handling(self):
        assert self._params.check_timer is not None
        assert self._params.remote_cfg is not None
        if self._params.check_timer.timed_out():
            self._params.current_check_count += 1
            if self._params.current_check_count == self._params.remote_cfg.check_limit:
                self._declare_fault(ConditionCode.CHECK_LIMIT_REACHED)
            else:
                self._params.check_timer.reset()

    def _declare_fault(self, cond: ConditionCode) -> FaultHandlerCode:
        fh = self.cfg.default_fault_handlers.get_fault_handler(cond)
        if fh is None:
            raise ValueError(f"invalid condition code {cond!r} for fault declaration")
        if fh == FaultHandlerCode.NOTICE_OF_CANCELLATION:
            self._notice_of_cancellation(cond)
        elif fh == FaultHandlerCode.NOTICE_OF_SUSPENSION:
            self._notice_of_suspension()
        elif fh == FaultHandlerCode.ABANDON_TRANSACTION:
            self._abandon_transaction()
        self.cfg.default_fault_handlers.report_fault(cond)
        return fh

    def _notice_of_cancellation(self, condition_code: ConditionCode):
        # TODO: Implement
        pass

    def _notice_of_suspension(self):
        # TODO: Implement
        pass

    def _abandon_transaction(self):
        # I guess an abandoned transaction just stops whatever it is doing.. The implementation
        # for this is quite easy.
        self.reset()
