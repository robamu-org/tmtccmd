import enum
import logging
from dataclasses import dataclass
from typing import Optional, Dict, List

from spacepackets.cfdp import (
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
    FileDeliveryStatus,
    DeliveryCode,
    EofPdu,
    FileDataPdu,
    MetadataPdu,
    MetadataParams,
    DirectiveType,
    AbstractFileDirectiveBase,
)
from spacepackets.cfdp.pdu.file_data import FileDataParams
from spacepackets.util import UnsignedByteField, ByteFieldGenerator
from tmtccmd.cfdp import (
    LocalEntityCfg,
    CfdpUserBase,
    TransactionId,
    RemoteEntityCfg,
)
from tmtccmd.cfdp.defs import CfdpRequestType, CfdpStates
from tmtccmd.cfdp.filestore import VirtualFilestore
from tmtccmd.cfdp.handler.crc import Crc32Helper
from tmtccmd.cfdp.handler.defs import (
    FileParamsBase,
    PacketSendNotConfirmed,
    SourceFileDoesNotExist,
    InvalidPduDirection,
    InvalidSourceId,
    InvalidDestinationId,
)
from tmtccmd.cfdp.mib import EntityType
from tmtccmd.cfdp.request import CfdpRequestWrapper, PutRequest
from tmtccmd.cfdp.user import TransactionFinishedParams
from tmtccmd.util import ProvidesSeqCount
from tmtccmd.util.countdown import Countdown

_LOGGER = logging.getLogger(__name__)


class TransactionStep(enum.Enum):
    IDLE = 0
    TRANSACTION_START = 1
    CRC_PROCEDURE = 2
    # The following three are used for the Copy File Procedure
    SENDING_METADATA = 3
    SENDING_FILE_DATA = 4
    SENDING_EOF = 5
    WAIT_FOR_ACK = 6
    WAIT_FOR_FINISH = 7
    NOTICE_OF_COMPLETION = 8


@dataclass
class SourceStateWrapper:
    state: CfdpStates = CfdpStates.IDLE
    step: TransactionStep = TransactionStep.IDLE
    packet_ready: bool = False


class TransferFieldWrapper:
    def __init__(self, local_entity_id: UnsignedByteField, vfs: VirtualFilestore):
        self.crc_helper = Crc32Helper(ChecksumType.NULL_CHECKSUM, vfs)
        self.transaction: Optional[TransactionId] = None
        self.check_limit: Optional[Countdown] = None
        self.fp = FileParamsBase.empty()
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


class FsmResult:
    def __init__(self, pdu_holder: PduHolder, states: SourceStateWrapper):
        self.pdu_holder = pdu_holder
        self.states = states


class InvalidPduForSourceHandler(Exception):
    def __init__(self, packet: AbstractFileDirectiveBase, *args, **kwargs):
        super().__init__(args, kwargs)
        self.packet = packet

    def __str__(self):
        return f"Invalid packet {self.packet} for source handler"


class SourceHandler:
    """This is the primary CFDP source handler. It models the CFDP source entity, which is primarily
    responsible for handling put requests to send files to another CFDP destination entity.

    As such, it contains a state machine to perform all operations necessary to perform a
    source-to-destination file transfer. This class does not send the CFDP PDU packets directly
    to allow for greater flexibility. For example, a user might want to wrap the CFDP packet
    entities into a CCSDS space packet or into a special frame type. The user is responsible for
    sending the packets and confirming that they are sent successfully.

    The following core functions are the primary interface for a direct usage or for a composite
    handler with a source handler and a destination handler as member objects:

     1. :py:meth:`start_transaction` : Can be used to start transactions, most notably to start
        and perform a Copy File procedure
     2. :py:meth:`state_machine` : This state machine generates the necessary CFDP PDUs necessary
        to perform a CFDP file transfer. The PDUs are returned in a special wrapper result type.
     3. :py:meth:`confirm_packet_sent_advance_fsm` : Confirm that the PDUs generated by the last
        state machine iteration was sent successfully and advance the state machine
     4. :py:meth:`pass_packet` : Pass reply PDUs received from a CFDP remote destination related
        to a specific transaction.

    """

    def __init__(
        self,
        cfg: LocalEntityCfg,
        seq_num_provider: ProvidesSeqCount,
        user: CfdpUserBase,
    ):
        self.states = SourceStateWrapper()
        self.pdu_holder = PduHolder(None)
        self.cfg = cfg
        self.user = user
        self.seq_num_provider = seq_num_provider
        self._params = TransferFieldWrapper(cfg.local_entity_id, self.user.vfs)
        self._current_req = CfdpRequestWrapper(None)
        self._rec_dict: Dict[DirectiveType, List[AbstractFileDirectiveBase]] = dict()

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

    def start_cfdp_transaction(
        self, wrapper: CfdpRequestWrapper, remote_cfg: RemoteEntityCfg
    ) -> bool:
        """Start a CFDP transaction.

        :param wrapper:
        :param remote_cfg:
        :return: Whether transaction was started successfully.
        """
        if wrapper.request_type == CfdpRequestType.PUT:
            return self.put_request(wrapper.to_put_request(), remote_cfg)

    def put_request(self, request: PutRequest, remote_cfg: RemoteEntityCfg):
        if self.states.state != CfdpStates.IDLE:
            _LOGGER.debug("CFDP source handler is busy, can't process put request")
            return False
        self._current_req.base = request
        self._params.remote_cfg = remote_cfg
        self._params.dest_id = remote_cfg.entity_id
        self.states.packet_ready = False
        self._setup_transmission_mode()
        if self._params.transmission_mode == TransmissionMode.UNACKNOWLEDGED:
            _LOGGER.debug("Starting Put Request handling in NAK mode")
            self.states.state = CfdpStates.BUSY_CLASS_1_NACKED
        elif self._params.transmission_mode == TransmissionMode.ACKNOWLEDGED:
            _LOGGER.debug("Starting Put Request handling in ACK mode")
            self.states.state = CfdpStates.BUSY_CLASS_2_ACKED
        else:
            raise ValueError(
                f"Invalid transmission mode {self._params.transmission_mode} passed"
            )
        return True

    def pass_packet(self, packet: AbstractFileDirectiveBase):
        """Pass PDU file directives going towards the file sender to the CFDP source handler

        :raises InvalidPduDirection: PDU direction field wrong
        :raises InvalidPduForSourceHandler: Invalid PDU file directive type
        """
        if packet.pdu_header.direction != Direction.TOWARDS_SENDER:
            raise InvalidPduDirection(
                Direction.TOWARDS_SENDER, packet.pdu_header.direction
            )
        if packet.source_entity_id != self.source_id:
            raise InvalidSourceId(self.source_id, packet.source_entity_id)
        if packet.dest_entity_id != self._params.remote_cfg.entity_id:
            raise InvalidDestinationId(
                self._params.remote_cfg.entity_id, packet.dest_entity_id
            )
        # TODO: What about prompt and keep alive PDU?
        if packet.directive_type in [
            DirectiveType.METADATA_PDU,
            DirectiveType.EOF_PDU,
        ]:
            raise InvalidPduForSourceHandler(packet)
        # A dictionary is used to allow passing multiple received packets and store them until
        # they are processed by the state machine.
        if packet.directive_type in self._rec_dict:
            pdu_directive_list = self._rec_dict.get(packet.directive_type)
            pdu_directive_list.append(packet)
        else:
            self._rec_dict.update({packet.directive_type: [packet]})

    def __fsm_crc_procedure(self, put_req: PutRequest):
        if self._params.fp.file_size == 0:
            # Empty file, use null checksum
            self._params.fp.crc32 = NULL_CHECKSUM_U32
        else:
            self._params.fp.crc32 = self._params.crc_helper.calc_for_file(
                file=put_req.cfg.source_file,
                file_sz=self._params.fp.file_size,
                segment_len=self._params.fp.segment_len,
            )

        self.states.step = TransactionStep.SENDING_METADATA

    def __fsm_naked(  # noqa: C901  # complexity is okay here
        self,
    ) -> Optional[FsmResult]:
        put_req = self._current_req.to_put_request()
        if self.states.step == TransactionStep.IDLE:
            self.states.step = TransactionStep.TRANSACTION_START
        if self.states.step == TransactionStep.TRANSACTION_START:
            self._transaction_start(put_req)
            self.states.step = TransactionStep.CRC_PROCEDURE
        if self.states.step == TransactionStep.CRC_PROCEDURE:
            self.__fsm_crc_procedure(put_req)
        if self.states.step == TransactionStep.SENDING_METADATA:
            self._prepare_metadata_pdu(put_req)
            self.states.packet_ready = True
            return FsmResult(self.pdu_holder, self.states)
        if self.states.step == TransactionStep.SENDING_FILE_DATA:
            if self._prepare_next_file_data_pdu(put_req):
                self.states.packet_ready = True
                return FsmResult(self.pdu_holder, self.states)
            else:
                # Special case: Empty file.
                self.states.step = TransactionStep.SENDING_EOF
        if self.states.step == TransactionStep.SENDING_EOF:
            self._prepare_eof_pdu()
            self.states.packet_ready = True
            return FsmResult(self.pdu_holder, self.states)
        if self.states.step == TransactionStep.WAIT_FOR_ACK:
            self._handle_wait_for_ack()
        if self.states.step == TransactionStep.WAIT_FOR_FINISH:
            self._handle_wait_for_finish()
        if self.states.step == TransactionStep.NOTICE_OF_COMPLETION:
            self._notice_of_completion()

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
        if self.states.state == CfdpStates.IDLE:
            return FsmResult(self.pdu_holder, self.states)
        elif self.states.state == CfdpStates.BUSY_CLASS_1_NACKED:
            fsm_res = self.__fsm_naked()
            if fsm_res is not None:
                return fsm_res
        return FsmResult(self.pdu_holder, self.states)

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
        """Advance the internal FSM. This call is necessary to walk through the various steps
        of a CFDP transaction. This step is not done in the main :py:meth:`operation` call
        because the packets generated by this method need to be sent first and then confirmed
        via the :py:meth:`confirm_packet_sent` function.

        :return:
        """
        if self.states.packet_ready:
            raise PacketSendNotConfirmed(
                f"Must send current packet {self.pdu_holder.base} before "
                f"advancing state machine"
            )
        if self.states.state == CfdpStates.BUSY_CLASS_1_NACKED:
            if self.states.step == TransactionStep.SENDING_METADATA:
                self.states.step = TransactionStep.SENDING_FILE_DATA
            elif self.states.step == TransactionStep.SENDING_FILE_DATA:
                self._handle_file_data_sent()
            elif self.states.step == TransactionStep.SENDING_EOF:
                self._handle_eof_sent()

    def reset(self):
        self.states.step = TransactionStep.IDLE
        self.states.state = CfdpStates.IDLE
        self._params.reset()

    def _handle_eof_sent(self):
        if self.cfg.indication_cfg.eof_sent_indication_required:
            self.user.eof_sent_indication(self._params.transaction)
        if self.states.state == CfdpStates.BUSY_CLASS_1_NACKED:
            if self._params.closure_requested:
                if self._params.remote_cfg.check_limit is not None:
                    self._params.check_limit = (
                        self._params.remote_cfg.check_limit.provide_check_limit(
                            local_entity_id=self.cfg.local_entity_id,
                            remote_entity_id=self._params.remote_cfg.entity_id,
                            entity_type=EntityType.SENDING,
                        )
                    )
                self.states.step = TransactionStep.WAIT_FOR_FINISH
            else:
                self.states.step = TransactionStep.NOTICE_OF_COMPLETION
        else:
            self.states.step = TransactionStep.WAIT_FOR_ACK

    def _handle_file_data_sent(self):
        if self._params.fp.progress == self._params.fp.file_size:
            self.states.step = TransactionStep.SENDING_EOF

    def _handle_wait_for_ack(self):
        if self.states.state != CfdpStates.BUSY_CLASS_2_ACKED:
            _LOGGER.error(
                f"Invalid ACK waiting function call for state {self.states.state}"
            )
        pdu_list = self._rec_dict.get(DirectiveType.ACK_PDU)
        if pdu_list is None:
            return FsmResult(self.pdu_holder, self.states)
        for pdu in pdu_list:
            holder = PduHolder(pdu)
            ack_pdu = holder.to_ack_pdu()
            if ack_pdu.directive_code_of_acked_pdu == DirectiveType.EOF_PDU:
                if ack_pdu.condition_code_of_acked_pdu != ConditionCode.NO_ERROR:
                    # TODO: This is required for class 2 transfers. It might make sense
                    #       to remember the condition code of the sent EOF PDU for a basic
                    #       equality check here
                    pass
                self.states.step = TransactionStep.WAIT_FOR_FINISH

    def _notice_of_completion(self):
        if self.cfg.indication_cfg.transaction_finished_indication_required:
            indication_params = TransactionFinishedParams(
                transaction_id=self._params.transaction,
                condition_code=ConditionCode.NO_ERROR,
                file_status=FileDeliveryStatus.FILE_STATUS_UNREPORTED,
                delivery_code=DeliveryCode.DATA_COMPLETE,
            )
            self.user.transaction_finished_indication(indication_params)
        # Transaction finished
        self.reset()

    def _handle_wait_for_finish(self):
        if not self._params.closure_requested:
            _LOGGER.error(
                "Invalid Finish PDU waiting function call, no closure requested"
            )
        # TODO: If transaction closure is requested, a user transaction can only be marked
        #       as finished if TX finished PDU was received. This might take a long time
        #       so it might make sense to think about storing the current state of
        #       the transaction in a source state config file which can be restored
        #       when re-starting the application
        if self._params.closure_requested:
            if self._params.check_limit is not None:
                if self._params.check_limit.timed_out():
                    self._declare_fault(ConditionCode.CHECK_LIMIT_REACHED)
                    _LOGGER.warning(
                        f"Check limit countdown: {self._params.check_limit}"
                    )
            # Check all entries for some robustness against out-of-order reception
            if DirectiveType.FINISHED_PDU in self._rec_dict:
                pdu_list = self._rec_dict.get(DirectiveType.FINISHED_PDU)
                for pdu in pdu_list:
                    holder = PduHolder(pdu)
                    finish_pdu = holder.to_finished_pdu()
                    # TODO: I think there are some more conditions where we can issue a notice
                    #       of completion
                    if finish_pdu.condition_code == ConditionCode.NO_ERROR:
                        self.states.step = TransactionStep.NOTICE_OF_COMPLETION
                    else:
                        # TODO: Implement error handling
                        _LOGGER.warning(
                            f"Received condition code {finish_pdu.condition_code} in "
                            f"Finished PDU"
                        )

    def _setup_transmission_mode(self):
        put_req = self._current_req.to_put_request()
        # Transmission mode settings in the put request override settings from the remote MIB
        if put_req.cfg.trans_mode is not None:
            trans_mode_to_set = put_req.cfg.trans_mode
        else:
            trans_mode_to_set = self._params.remote_cfg.default_transmission_mode
        self._params.transmission_mode = trans_mode_to_set
        if put_req.cfg.closure_requested is not None:
            closure_req_to_set = put_req.cfg.closure_requested
        else:
            closure_req_to_set = self._params.remote_cfg.closure_requested
        self._params.crc_helper.checksum_type = self._params.remote_cfg.crc_type
        self._params.closure_requested = closure_req_to_set

    def _transaction_start(self, put_req: PutRequest):
        if not put_req.cfg.source_file.exists():
            # TODO: Handle this exception in the handler, reset CFDP state machine
            raise SourceFileDoesNotExist(put_req.cfg.source_file)
        size = put_req.cfg.source_file.stat().st_size
        if size == 0:
            self._params.fp.no_file_data = True
        else:
            self._params.fp.file_size = size
        self._params.fp.segment_len = self._params.remote_cfg.max_file_segment_len
        self._params.remote_cfg = self._params.remote_cfg
        self._get_next_transfer_seq_num()
        self._params.transaction = TransactionId(
            source_entity_id=self.cfg.local_entity_id,
            transaction_seq_num=self.transaction_seq_num,
        )
        self.user.transaction_indication(self._params.transaction)

    def _prepare_metadata_pdu(self, put_req: PutRequest):
        if self.states.packet_ready:
            raise PacketSendNotConfirmed(
                f"Must send current packet {self.pdu_holder.base} first"
            )
        self._params.pdu_conf.seg_ctrl = put_req.cfg.seg_ctrl
        self._params.pdu_conf.dest_entity_id = put_req.cfg.destination_id
        self._params.pdu_conf.crc_flag = self._params.remote_cfg.crc_on_transmission
        self._params.pdu_conf.direction = Direction.TOWARDS_RECEIVER
        params = MetadataParams(
            dest_file_name=put_req.cfg.dest_file,
            source_file_name=put_req.cfg.source_file.as_posix(),
            checksum_type=self._params.crc_helper.checksum_type,
            closure_requested=self._params.closure_requested,
            file_size=self._params.fp.file_size,
        )
        self.pdu_holder.base = MetadataPdu(
            pdu_conf=self._params.pdu_conf, params=params
        )

    def _prepare_next_file_data_pdu(self, request: PutRequest) -> bool:
        """Prepare the next file data PDU

        :param request:
        :return: True if a packet was prepared, False if PDU handling is done and the next steps
            in the Copy File procedure can be performed
        """
        # No need to send a file data PDU for an empty file
        if self._params.fp.no_file_data:
            return False
        with open(request.cfg.source_file, "rb") as of:
            if self._params.fp.progress == self._params.fp.file_size:
                return False
            if self.states.packet_ready:
                raise PacketSendNotConfirmed(
                    f"Must send current packet {self.pdu_holder.base} first"
                )
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
            file_data = self.user.vfs.read_from_opened_file(
                of, self._params.fp.progress, read_len
            )
            # TODO: Support for record continuation state not implemented yet. Segment metadata
            #       flag is therefore always set to False. Segment metadata support also omitted
            #       for now. Implementing those generically could be done in form of a callback,
            #       e.g. abstractmethod of this handler as a first way, another one being
            #       to expect the user to supply some helper class to split up a file
            fd_params = FileDataParams(
                file_data=file_data,
                offset=self._params.fp.progress,
                segment_metadata_flag=False,
            )
            file_data_pdu = FileDataPdu(
                pdu_conf=self._params.pdu_conf, params=fd_params
            )
            self._params.fp.progress += read_len
            self.pdu_holder.base = file_data_pdu
        return True

    def _prepare_eof_pdu(self):
        if self.states.packet_ready:
            raise PacketSendNotConfirmed(
                f"Must send current packet {self.pdu_holder.base} first"
            )
        self.pdu_holder.base = EofPdu(
            file_checksum=self._params.fp.crc32,
            file_size=self._params.fp.file_size,
            pdu_conf=self._params.pdu_conf,
        )

    def _get_next_transfer_seq_num(self):
        next_seq_num = self.seq_num_provider.get_and_increment()
        if self.seq_num_provider.max_bit_width not in [8, 16, 32]:
            raise ValueError(
                "Invalid bit width for sequence number provider, must be one of [8, 16, 32]"
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
            self._notice_of_cancellation()
        elif fh == FaultHandlerCode.NOTICE_OF_SUSPENSION:
            self._notice_of_suspension()
        elif fh == FaultHandlerCode.ABANDON_TRANSACTION:
            self._abandon_transaction()
        self.cfg.default_fault_handlers.report_fault(cond)

    def _notice_of_cancellation(self):
        # TODO: Implement
        pass

    def _notice_of_suspension(self):
        # TODO: Implement
        pass

    def _abandon_transaction(self):
        # TODO: Implement
        pass
