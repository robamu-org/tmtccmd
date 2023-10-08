from __future__ import annotations
from collections import deque
import enum
import logging
from dataclasses import dataclass
from typing import Deque, Optional, Tuple

import deprecation

from spacepackets.cfdp import (
    CrcFlag,
    GenericPduPacket,
    PduType,
    TransmissionMode,
    NULL_CHECKSUM_U32,
    ConditionCode,
    Direction,
    PduConfig,
    ChecksumType,
    FaultHandlerCode,
)
from spacepackets.cfdp.pdu import (
    PduHolder,
    EofPdu,
    FileDataPdu,
    MetadataPdu,
    AckPdu,
    MetadataParams,
    DirectiveType,
    AbstractFileDirectiveBase,
    TransactionStatus,
)
from spacepackets.cfdp.pdu.finished import FinishedParams
from spacepackets.cfdp.pdu.file_data import FileDataParams
from spacepackets.util import UnsignedByteField, ByteFieldGenerator
from tmtccmd.cfdp import (
    LocalEntityCfg,
    CfdpUserBase,
    TransactionId,
    RemoteEntityCfg,
)
from tmtccmd.cfdp.defs import CfdpState
from tmtccmd.cfdp.filestore import VirtualFilestore
from tmtccmd.cfdp.handler.crc import Crc32Helper
from tmtccmd.cfdp.handler.defs import (
    FileParamsBase,
    InvalidNakPdu,
    InvalidTransactionSeqNum,
    UnretrievedPdusToBeSent,
    SourceFileDoesNotExist,
    InvalidPduDirection,
    InvalidSourceId,
    InvalidDestinationId,
    NoRemoteEntityCfgFound,
    FsmNotCalledAfterPacketInsertion,
)
from tmtccmd.cfdp.mib import EntityType
from tmtccmd.cfdp.request import PutRequest
from tmtccmd.cfdp.user import TransactionFinishedParams
from tmtccmd.util import ProvidesSeqCount
from tmtccmd.util.countdown import Countdown
from tmtccmd.version import get_version

_LOGGER = logging.getLogger(__name__)


class TransactionStep(enum.Enum):
    IDLE = 0
    TRANSACTION_START = 1
    # The following three are used for the Copy File Procedure
    SENDING_METADATA = 3
    SENDING_FILE_DATA = 4
    SENDING_FILE_DATA_RETRANSMITTING = 5
    SENDING_EOF = 6
    WAITING_FOR_EOF_ACK = 7
    WAITING_FOR_FINISHED = 8
    SENDING_ACK_OF_FINISHED = 9
    NOTICE_OF_COMPLETION = 10


@dataclass
class _SourceFileParams(FileParamsBase):
    no_eof: bool = False

    @classmethod
    def empty(cls) -> _SourceFileParams:
        return cls(
            progress=0,
            segment_len=0,
            crc32=bytes(),
            file_size=0,
            no_eof=False,
            no_file_data=False,
        )

    def reset(self):
        super().reset()


@dataclass
class SourceStateWrapper:
    state: CfdpState = CfdpState.IDLE
    step: TransactionStep = TransactionStep.IDLE
    packets_ready: bool = False


class _TransferFieldWrapper:
    def __init__(self, local_entity_id: UnsignedByteField, vfs: VirtualFilestore):
        self.crc_helper = Crc32Helper(ChecksumType.NULL_CHECKSUM, vfs)
        self.transaction: Optional[TransactionId] = None
        self.check_limit: Optional[Countdown] = None
        self.fp = _SourceFileParams.empty()
        self.finished_params: Optional[FinishedParams] = None
        self.remote_cfg: Optional[RemoteEntityCfg] = None
        self.closure_requested: bool = False
        self.pdu_conf = PduConfig.empty()
        self.pdu_conf.source_entity_id = local_entity_id

    @property
    def source_id(self):
        return self.pdu_conf.source_entity_id

    @source_id.setter
    def source_id(self, source_id: UnsignedByteField):
        self.pdu_conf.source_entity_id = source_id

    @property
    def dest_id(self):
        return self.pdu_conf.dest_entity_id

    @dest_id.setter
    def dest_id(self, dest_id: UnsignedByteField):
        self.pdu_conf.dest_entity_id = dest_id

    @property
    def transmission_mode(self) -> TransmissionMode:
        return self.pdu_conf.trans_mode

    @transmission_mode.setter
    def transmission_mode(self, trans_mode: TransmissionMode):
        self.pdu_conf.trans_mode = trans_mode

    @property
    def transaction_seq_num(self) -> UnsignedByteField:
        return self.pdu_conf.transaction_seq_num

    @transaction_seq_num.setter
    def transaction_seq_num(self, seq_num: UnsignedByteField):
        self.pdu_conf.transaction_seq_num = seq_num

    def reset(self):
        self.fp.reset()
        self.remote_cfg = None
        self.transaction = None
        self.check_limit = None
        self.closure_requested = False
        self.pdu_conf = PduConfig.empty()
        self.finished_params = None


class FsmResult:
    def __init__(self, states: SourceStateWrapper):
        self.states = states


class InvalidPduForSourceHandler(Exception):
    def __init__(self, packet: AbstractFileDirectiveBase, *args, **kwargs):
        super().__init__(args, kwargs)
        self.packet = packet

    def __str__(self):
        return f"Invalid packet {self.packet} for source handler"


class PduIgnoredReason(enum.IntEnum):
    # The received PDU can only be used for acknowledged mode.
    ACK_MODE_PACKET_INVALID_MODE = 0
    # Received a Finished PDU, but source handler is currently not expecting one.
    NOT_WAITING_FOR_FINISHED_PDU = 1
    # Received a ACK PDU, but source handler is currently not expecting one.
    NOT_WAITING_FOR_ACK = 2


class PduIgnoredAtSource(Exception):
    def __init__(
        self, reason: PduIgnoredReason, ignored_packet: AbstractFileDirectiveBase
    ):
        self.ignored_packet = ignored_packet
        self.reason = reason
        super().__init__(f"ignored PDU packet at source handler: {reason!r}")


class _AckedModeContext:
    def __init__(self) -> None:
        self.segment_reqs_to_handle: Optional[Tuple[int, int]] = None
        self.segment_req_index: int = 0


class SourceHandler:
    """This is the primary CFDP source handler. It models the CFDP source entity, which is primarily
    responsible for handling put requests to send files to another CFDP destination entity.

    As such, it contains a state machine to perform all operations necessary to perform a
    source-to-destination file transfer. This class does not send the CFDP PDU packets directly
    to allow for greater flexibility. For example, a user might want to wrap the CFDP packet
    entities into a CCSDS space packet or into a special frame type. The user is responsible for
    sending the packets and confirming that they are sent successfully.

    The following core functions are the primary interface:

     1. :py:meth:`put_request` : Can be used to start transactions, most notably to start
        and perform a Copy File procedure to send a file or to send a Proxy Put Request to request
        a file.
     2. :py:meth:`insert_packet` : Can be used to insert packets into the source
        handler. Please note that the source handler can also process Finished, Keep Alive and
        NAK PDUs in addition to ACK PDUs where the acknowledged PDU is the EOF PDU.
     3. :py:meth:`state_machine` : This state machine generates the necessary CFDP PDUs necessary
        to perform a CFDP file transfer. The PDUs are returned in a special wrapper result type.
     4. :py:meth:`get_next_packet` : Retrieve the next packet which should be sent to the remote
        entity of a file copy operation. This function might also yield multiple packets on
        subsequent calls.

    A put request will only be accepted if the handler is in the idle state. Furthermore,
    packet insertion is not allowed until all packets to send were retrieved after a state machine
    call.

    This handler also does not support concurrency out of the box. Instead, if concurrent handling
    is required, it is recommended to create a new handler and run those inside a thread pool,
    or move the newly created handler to a new thread."""

    def __init__(
        self,
        cfg: LocalEntityCfg,
        seq_num_provider: ProvidesSeqCount,
        user: CfdpUserBase,
    ):
        self.states = SourceStateWrapper()
        self.cfg = cfg
        self.user = user
        self.seq_num_provider = seq_num_provider
        self._params = _TransferFieldWrapper(cfg.local_entity_id, self.user.vfs)
        self._put_req: Optional[PutRequest] = None
        self._ack_ctx: _AckedModeContext = _AckedModeContext()
        self._inserted_pdu = PduHolder(None)
        self._pdus_to_be_sent: Deque[PduHolder] = deque()

    @property
    def transaction_seq_num(self) -> UnsignedByteField:
        return self.pdu_conf.transaction_seq_num

    @property
    def pdu_conf(self) -> PduConfig:
        return self._params.pdu_conf

    @property
    def source_id(self) -> UnsignedByteField:
        return self.cfg.local_entity_id

    @source_id.setter
    def source_id(self, source_id: UnsignedByteField):
        self.cfg.local_entity_id = source_id
        self._params.source_id = source_id

    def put_request(self, request: PutRequest, remote_cfg: RemoteEntityCfg):
        """You can call this function to pass a put request to the source handler, which is
        also used to start a file copy operation. Please note that the source handler can
        also process one put request at a time.
        The caller is responsible of creating a new source handler, one handler can only handle
        one file copy request at a time.

        :return: False if the handler is busy. True if the handling of the request was successfull.
        :raise ValueError: Invalid transmission mode detected."""
        if self.states.state != CfdpState.IDLE:
            _LOGGER.debug("CFDP source handler is busy, can't process put request")
            return False
        self._put_req = request
        self._params.remote_cfg = remote_cfg
        self._params.dest_id = remote_cfg.entity_id
        self.states.packets_ready = False
        self._setup_transmission_mode()
        if self._params.transmission_mode == TransmissionMode.UNACKNOWLEDGED:
            _LOGGER.debug("Starting Put Request handling in NAK mode")
            self.states.state = CfdpState.BUSY_CLASS_1_NACKED
        elif self._params.transmission_mode == TransmissionMode.ACKNOWLEDGED:
            _LOGGER.debug("Starting Put Request handling in ACK mode")
            self.states.state = CfdpState.BUSY_CLASS_2_ACKED
        else:
            raise ValueError(
                f"Invalid transmission mode {self._params.transmission_mode} passed"
            )
        return True

    def cancel_request(self, transaction_id: TransactionId) -> bool:
        if (
            self._params.transaction is not None
            and transaction_id == self._params.transaction
        ):
            self._declare_fault(ConditionCode.CANCEL_REQUEST_RECEIVED)
            return True
        return False

    @deprecation.deprecated(
        deprecated_in="6.0.0rc1",
        current_version=get_version(),
        details="Use insert_packet instead",
    )
    def pass_packet(self, packet: AbstractFileDirectiveBase):
        self.insert_packet(packet)

    def insert_packet(self, packet: AbstractFileDirectiveBase):
        """Pass PDU file directives going towards the file sender to the CFDP source handler.
        Please note that only one packet can be inserted into the source handler at a given time.
        The packet is then handled by calling the :py:meth:`state_machine` and will be
        cleared after the packet was successfully handled, allowing insertion of new packets.

        :raises InvalidPduDirection: PDU direction field wrong.
        :raises FsmNotCalledAfterPacketInsertion: :py:meth:`state_machine` was not called after
            packet insertion.
        :raises InvalidPduForSourceHandler: Invalid PDU file directive type.
        :raises PduIgnoredAtSource: The specified PDU can not be handled in the current state.
        :raises NoRemoteEntityCfgFound: No remote configuration found for specified destination
            entity.
        :raises InvalidDestinationId: Destination ID was found, but there is a mismatch between
            the packet destination ID and the remote configuration entity ID."""
        if self._inserted_pdu.pdu is not None:
            raise FsmNotCalledAfterPacketInsertion()
        if packet.pdu_header.direction != Direction.TOWARDS_SENDER:
            raise InvalidPduDirection(
                Direction.TOWARDS_SENDER, packet.pdu_header.direction
            )
        if packet.source_entity_id != self.source_id:
            raise InvalidSourceId(self.source_id, packet.source_entity_id)
        # TODO: This can happen if a packet is received for which no transaction was started..
        #       A better exception might be worth a thought..
        if self._params.remote_cfg is None:
            raise NoRemoteEntityCfgFound(entity_id=packet.dest_entity_id)
        if packet.dest_entity_id != self._params.remote_cfg.entity_id:
            raise InvalidDestinationId(
                self._params.remote_cfg.entity_id, packet.dest_entity_id
            )

        if packet.transaction_seq_num != self._params.transaction_seq_num:
            raise InvalidTransactionSeqNum(
                self._params.transaction_seq_num, packet.transaction_seq_num
            )
        if packet.directive_type in [
            DirectiveType.METADATA_PDU,
            DirectiveType.EOF_PDU,
            DirectiveType.PROMPT_PDU,
        ]:
            raise InvalidPduForSourceHandler(packet)
        if self._params.transmission_mode == TransmissionMode.UNACKNOWLEDGED and (
            packet.directive_type == DirectiveType.KEEP_ALIVE_PDU
            or packet.directive_type == DirectiveType.NAK_PDU
        ):
            raise PduIgnoredAtSource(
                reason=PduIgnoredReason.ACK_MODE_PACKET_INVALID_MODE,
                ignored_packet=packet,
            )
        if (
            self.states.step == TransactionStep.WAITING_FOR_EOF_ACK
            and packet.directive_type != DirectiveType.ACK_PDU
        ):
            raise PduIgnoredAtSource(
                reason=PduIgnoredReason.NOT_WAITING_FOR_ACK, ignored_packet=packet
            )
        if (
            self.states.step == TransactionStep.WAITING_FOR_FINISHED
            and packet.directive_type != DirectiveType.FINISHED_PDU
        ):
            raise PduIgnoredAtSource(
                reason=PduIgnoredReason.NOT_WAITING_FOR_FINISHED_PDU,
                ignored_packet=packet,
            )
        self._inserted_pdu.pdu = packet

    def get_next_packet(self) -> Optional[PduHolder]:
        if len(self._pdus_to_be_sent) == 0:
            return None
        return self._pdus_to_be_sent.popleft()

    def state_machine(self) -> FsmResult:
        """This is the primary state machine which performs the CFDP procedures like CRC calculation
        and PDU generation. The packets generated by this finite-state machine (FSM) need to be
        sent by the user and can be retrieved using the
        :py:class:`spacepackets.cfdp.pdu.helper.PduHolder` class contained in the
        returned :py:class:`tmtccmd.cfdp.handler.source.FsmResult`. After the packet was sent,
        the calling code has to call :py:meth:`confirm_packet_sent` and :py:meth:`advance_fsm`
        for the next state machine call do perform the next transaction step.
        There is also the helper method :py:meth:`confirm_packet_sent_advance_fsm` available
        to perform both steps.

        :raises PacketSendNotConfirmed: The FSM generated a packet to be sent but the packet send
            was not confirmed
        :raises ChecksumNotImplemented: Right now, only a subset of the checksums specified for
            the CFDP standard are implemented.
        :raises SourceFileDoesNotExist: The source file for which a transaction was requested
            does not exist.
        """
        if self.states.state == CfdpState.IDLE:
            return FsmResult(self.states)
        self._fsm_non_idle()
        return FsmResult(self.states)

    def reset(self):
        """This function is public to allow completely resetting the handler, but it is explicitely
        discouraged to do this. CFDP generally has mechanism to detect issues and errors on itself.
        """
        self.states.step = TransactionStep.IDLE
        self.states.state = CfdpState.IDLE
        self._pdus_to_be_sent.clear()
        self._params.reset()

    def _fsm_non_idle(self):
        self._fsm_advancement_after_packets_were_sent()
        if self._put_req is None:
            return
        if self.states.step == TransactionStep.IDLE:
            self.states.step = TransactionStep.TRANSACTION_START
        if self.states.step == TransactionStep.TRANSACTION_START:
            self._transaction_start()
            self.states.step = TransactionStep.SENDING_METADATA
        if self.states.step == TransactionStep.SENDING_METADATA:
            self._prepare_metadata_pdu()
            return
        if self.states.step == TransactionStep.SENDING_FILE_DATA:
            if self._sending_file_data_fsm():
                return
        if self.states.step == TransactionStep.SENDING_EOF:
            self._prepare_eof_pdu(
                ConditionCode.NO_ERROR,
                self._checksum_calculation(self._params.fp.file_size),
            )
            return
        if self.states.step == TransactionStep.WAITING_FOR_EOF_ACK:
            self._handle_wait_for_ack()
        if self.states.step == TransactionStep.WAITING_FOR_FINISHED:
            self._handle_wait_for_finish()
        if self.states.step == TransactionStep.NOTICE_OF_COMPLETION:
            self._notice_of_completion()

    def _transaction_start(self):
        assert self._put_req is not None
        if self._put_req.metadata_only:
            self._params.fp.no_file_data = True
            self._params.fp.no_eof = True
        else:
            assert self._put_req.source_file is not None
            if not self._put_req.source_file.exists():
                # TODO: Handle this exception in the handler, reset CFDP state machine
                raise SourceFileDoesNotExist(self._put_req.source_file)
            size = self._put_req.source_file.stat().st_size
            if size == 0:
                self._params.fp.no_file_data = True
            else:
                self._params.fp.file_size = size
        assert self._params.remote_cfg is not None
        self._params.fp.segment_len = self._params.remote_cfg.max_file_segment_len
        self._get_next_transfer_seq_num()
        self._params.transaction = TransactionId(
            source_entity_id=self.cfg.local_entity_id,
            transaction_seq_num=self.transaction_seq_num,
        )
        self.user.transaction_indication(self._params.transaction)

    def _prepare_metadata_pdu(self):
        assert self._put_req is not None
        options = []
        if self._put_req.metadata_only:
            params = MetadataParams(
                closure_requested=self._params.closure_requested,
                checksum_type=self._params.crc_helper.checksum_type,
                file_size=0,
                dest_file_name=None,
                source_file_name=None,
            )
        else:
            # Funny name.
            params = self._prepare_metadata_base_params_with_metadata()
        if self._put_req.fs_requests is not None:
            for fs_request in self._put_req.fs_requests:
                options.append(fs_request)
        if self._put_req.fault_handler_overrides is not None:
            for fh_override in self._put_req.fault_handler_overrides:
                options.append(fh_override)
        if self._put_req.flow_label_tlv is not None:
            options.append(self._put_req.flow_label_tlv)
        if self._put_req.msgs_to_user is not None:
            for msg_to_user in self._put_req.msgs_to_user:
                options.append(msg_to_user)
        self._add_packet_to_be_sent(
            MetadataPdu(pdu_conf=self._params.pdu_conf, params=params, options=options)
        )

    def _prepare_metadata_base_params_with_metadata(self) -> MetadataParams:  # type: ignore
        if self._put_req.seg_ctrl is not None:  # type: ignore
            self._params.pdu_conf.seg_ctrl = self._put_req.seg_ctrl  # type: ignore
        self._params.pdu_conf.dest_entity_id = self._put_req.destination_id  # type: ignore
        self._params.pdu_conf.crc_flag = CrcFlag(
            self._params.remote_cfg.crc_on_transmission  # type: ignore
        )
        self._params.pdu_conf.direction = Direction.TOWARDS_RECEIVER
        return MetadataParams(
            dest_file_name=self._put_req.dest_file.as_posix(),  # type: ignore
            source_file_name=self._put_req.source_file.as_posix(),  # type: ignore
            checksum_type=self._params.crc_helper.checksum_type,
            closure_requested=self._params.closure_requested,
            file_size=self._params.fp.file_size,
        )

    def _sending_file_data_fsm(self) -> bool:
        """This function returns whether the internal state was advanced or not."""
        # During the PDU send phase, handle the re-transmission of missing files in
        # acknowledged mode.
        if self.states.state == CfdpState.BUSY_CLASS_2_ACKED:
            if self.__handle_retransmission():
                return True
        if self._prepare_progressing_file_data_pdu():
            self.states.packets_ready = True
            return True
        if self._params.fp.no_eof:
            # Special case: Metadata Only.
            if self._params.closure_requested:
                self.states.step = TransactionStep.WAITING_FOR_FINISHED
            else:
                self.states.step = TransactionStep.NOTICE_OF_COMPLETION
        else:
            # Special case: Empty file.
            self.states.step = TransactionStep.SENDING_EOF
        return False

    def __handle_retransmission(self) -> bool:
        if self._inserted_pdu.pdu is None:
            return False
        if self._inserted_pdu.pdu_directive_type != DirectiveType.NAK_PDU:
            return False
        nak_pdu = self._inserted_pdu.to_nak_pdu()
        packet_prepared = False
        for segment_req in nak_pdu.segment_requests:
            # Special case: Metadata PDU is re-requested
            if segment_req[0] == 0 and segment_req[1] == 0:
                # Re-transmit the metadata PDU
                self._prepare_metadata_pdu()
                packet_prepared = True
            else:
                if segment_req[1] < segment_req[0]:
                    raise InvalidNakPdu("end offset larger than start offset")
                elif segment_req[0] > self._params.fp.progress:
                    raise InvalidNakPdu(
                        "start offset larger than current file progress"
                    )
                self._prepare_file_data_pdu(
                    segment_req[0], segment_req[1] - segment_req[0]
                )
                packet_prepared = True
        return packet_prepared

    def _handle_wait_for_ack(self):
        if self.states.state != CfdpState.BUSY_CLASS_2_ACKED:
            _LOGGER.error(
                f"Invalid ACK waiting function call for state {self.states.state}"
            )
        if self._inserted_pdu.base is None:
            return FsmResult(self.states)
        if (
            self._inserted_pdu.pdu_type == PduType.FILE_DIRECTIVE
            and self._inserted_pdu.pdu_directive_type != DirectiveType.ACK_PDU
        ):
            return FsmResult(self.states)
        ack_pdu = self._inserted_pdu.to_ack_pdu()
        if ack_pdu.directive_code_of_acked_pdu == DirectiveType.EOF_PDU:
            if ack_pdu.condition_code_of_acked_pdu != ConditionCode.NO_ERROR:
                # TODO: This is required for class 2 transfers. It might make sense
                #       to remember the condition code of the sent EOF PDU for a basic
                #       equality check here
                pass
            self.states.step = TransactionStep.WAITING_FOR_FINISHED

    def _handle_wait_for_finish(self):
        if (
            (
                self.states.state == CfdpState.BUSY_CLASS_1_NACKED
                and not self._params.closure_requested
            )
            or self._inserted_pdu.pdu is None
            or self._inserted_pdu.pdu_directive_type is None
            or self._inserted_pdu.pdu_directive_type != DirectiveType.FINISHED_PDU
        ):
            # TODO: Store finished PDU parameters for later processing in the notice of completion.
            if self._params.check_limit is not None:
                if self._params.check_limit.timed_out():
                    _LOGGER.warning(
                        f"Check limit countdown: {self._params.check_limit}"
                    )
                    self._declare_fault(ConditionCode.CHECK_LIMIT_REACHED)
            return
        finished_pdu = self._inserted_pdu.to_finished_pdu()
        self._inserted_pdu.pdu = None
        if self.states.state == CfdpState.BUSY_CLASS_2_ACKED:
            self._prepare_finished_ack_packet(finished_pdu.condition_code)
            self.states.step = TransactionStep.SENDING_ACK_OF_FINISHED
        else:
            self.states.step = TransactionStep.NOTICE_OF_COMPLETION
            self._params.finished_params = finished_pdu.finished_params

    def _notice_of_completion(self):
        if self.cfg.indication_cfg.transaction_finished_indication_required:
            assert self._params.transaction is not None
            assert self._params.finished_params is not None
            indication_params = TransactionFinishedParams(
                transaction_id=self._params.transaction,
                condition_code=self._params.finished_params.condition_code,
                file_status=self._params.finished_params.delivery_status,
                delivery_code=self._params.finished_params.delivery_code,
                fs_responses=self._params.finished_params.file_store_responses,
            )
            self.user.transaction_finished_indication(indication_params)
        # Transaction finished
        self.reset()

    def _fsm_advancement_after_packets_were_sent(self):
        """Advance the internal FSM after all packets to be sent were retrieved from the handler."""
        if len(self._pdus_to_be_sent) > 0:
            raise UnretrievedPdusToBeSent(
                f"{len(self._pdus_to_be_sent)} packets left to send"
            )
        if self.states.state == CfdpState.BUSY_CLASS_1_NACKED:
            if self.states.step == TransactionStep.SENDING_METADATA:
                self.states.step = TransactionStep.SENDING_FILE_DATA
            elif self.states.step == TransactionStep.SENDING_FILE_DATA_RETRANSMITTING:
                self.states.step = TransactionStep.SENDING_FILE_DATA
            elif self.states.step == TransactionStep.SENDING_FILE_DATA:
                self._handle_file_data_sent()
            elif self.states.step == TransactionStep.SENDING_EOF:
                self._handle_eof_sent()

    def _handle_eof_sent(self):
        if self.cfg.indication_cfg.eof_sent_indication_required:
            assert self._params.transaction is not None
            self.user.eof_sent_indication(self._params.transaction)
        if self.states.state == CfdpState.BUSY_CLASS_1_NACKED:
            if self._params.closure_requested:
                assert self._params.remote_cfg is not None
                if self._params.remote_cfg.check_limit_provider is not None:
                    self._params.check_limit = self._params.remote_cfg.check_limit_provider.provide_check_limit(
                        local_entity_id=self.cfg.local_entity_id,
                        remote_entity_id=self._params.remote_cfg.entity_id,
                        entity_type=EntityType.SENDING,
                    )
                self.states.step = TransactionStep.WAITING_FOR_FINISHED
            else:
                self.states.step = TransactionStep.NOTICE_OF_COMPLETION
        else:
            self.states.step = TransactionStep.WAITING_FOR_EOF_ACK

    def _handle_file_data_sent(self):
        if self._params.fp.progress == self._params.fp.file_size:
            self.states.step = TransactionStep.SENDING_EOF

    def _prepare_finished_ack_packet(self, condition_code: ConditionCode):
        ack_pdu = AckPdu(
            self._params.pdu_conf,
            DirectiveType.FINISHED_PDU,
            condition_code,
            TransactionStatus.ACTIVE,
        )
        self._add_packet_to_be_sent(ack_pdu)

    def _setup_transmission_mode(self):
        assert self._put_req is not None
        assert self._params.remote_cfg is not None
        # Transmission mode settings in the put request override settings from the remote MIB
        if self._put_req.trans_mode is not None:
            trans_mode_to_set = self._put_req.trans_mode
        else:
            trans_mode_to_set = self._params.remote_cfg.default_transmission_mode
        self._params.transmission_mode = trans_mode_to_set
        if self._put_req.closure_requested is not None:
            closure_req_to_set = self._put_req.closure_requested
        else:
            closure_req_to_set = self._params.remote_cfg.closure_requested
        self._params.crc_helper.checksum_type = self._params.remote_cfg.crc_type
        self._params.closure_requested = closure_req_to_set

    def _add_packet_to_be_sent(self, packet: GenericPduPacket):
        self._pdus_to_be_sent.append(PduHolder(packet))
        self.states.packets_ready = True

    def _prepare_progressing_file_data_pdu(self) -> bool:
        """Prepare the next file data PDU, which also progresses the file copy operation.

        :return: True if a packet was prepared, False if PDU handling is done and the next steps
            in the Copy File procedure can be performed
        """
        # No need to send a file data PDU for an empty file
        if self._params.fp.no_file_data:
            return False
        if self._params.fp.progress == self._params.fp.file_size:
            return False
        if self._params.fp.file_size < self._params.fp.segment_len:
            read_len = self._params.fp.file_size
        else:
            if (
                self._params.fp.progress + self._params.fp.segment_len
                > self._params.fp.file_size
            ):
                read_len = self._params.fp.file_size - self._params.fp.progress
            else:
                read_len = self._params.fp.segment_len
        self._prepare_file_data_pdu(self._params.fp.progress, read_len)
        self._params.fp.progress += read_len
        return True

    def _prepare_file_data_pdu(self, offset: int, read_len: int):
        """Generic function to prepare a file data PDU. This function can also be used to
        re-transmit file data PDUs of segments which were already sent."""
        assert self._put_req is not None
        assert self._put_req.source_file is not None
        with open(self._put_req.source_file, "rb") as of:
            file_data = self.user.vfs.read_from_opened_file(of, offset, read_len)
            # TODO: Support for record continuation state not implemented yet. Segment metadata
            #       flag is therefore always set to False. Segment metadata support also omitted
            #       for now. Implementing those generically could be done in form of a callback,
            #       e.g. abstractmethod of this handler as a first way, another one being
            #       to expect the user to supply some helper class to split up a file
            fd_params = FileDataParams(
                file_data=file_data,
                offset=offset,
                segment_metadata_flag=False,
            )
            file_data_pdu = FileDataPdu(
                pdu_conf=self._params.pdu_conf, params=fd_params
            )
            self._add_packet_to_be_sent(file_data_pdu)

    def _prepare_eof_pdu(self, condition_code: ConditionCode, checksum: bytes):
        self._add_packet_to_be_sent(
            EofPdu(
                file_checksum=checksum,
                file_size=self._params.fp.progress,
                pdu_conf=self._params.pdu_conf,
                condition_code=condition_code,
            )
        )

    def _get_next_transfer_seq_num(self):
        next_seq_num = self.seq_num_provider.get_and_increment()
        if self.seq_num_provider.max_bit_width not in [8, 16, 32]:
            raise ValueError(
                "Invalid bit width for sequence number provider, must be one of [8,"
                " 16, 32]"
            )
        self._params.pdu_conf.transaction_seq_num = ByteFieldGenerator.from_int(
            self.seq_num_provider.max_bit_width // 8, next_seq_num
        )

    def _declare_fault(self, cond: ConditionCode):
        _LOGGER.warning(
            f"Fault with condition code {cond} was declared for "
            f"transaction {self._params.transaction}"
        )
        fh = self.cfg.default_fault_handlers.get_fault_handler(cond)
        if fh == FaultHandlerCode.NOTICE_OF_CANCELLATION:
            self._notice_of_cancellation(cond)
        elif fh == FaultHandlerCode.NOTICE_OF_SUSPENSION:
            self._notice_of_suspension()
        elif fh == FaultHandlerCode.ABANDON_TRANSACTION:
            self._abandon_transaction()
        self.cfg.default_fault_handlers.report_fault(cond)

    def _notice_of_cancellation(self, condition_code: ConditionCode):
        # As specified in 4.11.2.2, prepare an EOF PDU to be sent to the remote entity. Supply
        # the checksum for the file copy progress sent so far.
        self._prepare_eof_pdu(
            condition_code, self._checksum_calculation(self._params.fp.progress)
        )

    def _notice_of_suspension(self):
        # TODO: Implement
        pass

    def _abandon_transaction(self):
        # I guess an abandoned transaction just stops whatever it is doing.. The implementation
        # for this is quite easy.
        self.reset()

    def _checksum_calculation(self, size_to_calculate: int) -> bytes:
        if self._params.fp.file_size == 0:
            # Empty file, use null checksum
            crc = NULL_CHECKSUM_U32
        else:
            assert self._put_req is not None
            assert self._put_req.source_file is not None
            crc = self._params.crc_helper.calc_for_file(
                file=self._put_req.source_file,
                file_sz=size_to_calculate,
                segment_len=self._params.fp.segment_len,
            )
        return crc
