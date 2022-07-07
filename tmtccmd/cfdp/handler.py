import dataclasses
from pathlib import Path
from typing import Optional
from crcmod.predefined import PredefinedCrc

from spacepackets.cfdp.pdu import PduWrapper, EofPdu
from spacepackets.cfdp.pdu.file_data import FileDataPdu
from spacepackets.cfdp.pdu.finished import FileDeliveryStatus, DeliveryCode
from tmtccmd.logging import get_console_logger

from spacepackets.cfdp.pdu.metadata import MetadataPdu
from spacepackets.cfdp.conf import PduConfig
from spacepackets.cfdp.defs import (
    ChecksumTypes,
    Direction,
    UnsignedByteField,
    ByteFieldU8,
    ByteFieldU16,
    ByteFieldU32,
    ConditionCode,
)
from .defs import (
    CfdpStates,
    BusyError,
    CfdpRequestType,
    SourceTransactionState,
    SourceState,
    SourceStateWrapper,
    StateWrapper,
    TransactionId,
)
from .mib import LocalEntityCfg, RemoteEntityTable, RemoteEntityCfg
from .request import CfdpRequestWrapper, PutRequest
from .user import CfdpUserBase
from ..com_if import ComInterface
from ..util import ProvidesSeqCount

LOGGER = get_console_logger()


class CfdpResult:
    def __init__(self):
        pass


@dataclasses.dataclass
class FileParams:
    offset = 0
    segment_len = 0
    crc32 = bytes()
    size = 0

    def reset(self):
        self.offset = 0
        self.segment_len = 0
        self.crc32 = bytes()
        self.size = 0


class TransferFieldWrapper:
    def __init__(self, local_entity_id: UnsignedByteField):
        self.pdu_wrapper = PduWrapper(None)
        self.transaction: Optional[TransactionId] = None
        self.fp = FileParams()
        self.remote_cfg: Optional[RemoteEntityCfg] = None
        self.pdu_conf = PduConfig.empty()
        self.pdu_conf.source_entity_id = local_entity_id

    def reset(self):
        self.pdu_wrapper.base = None
        self.fp.reset()
        self.remote_cfg = None


class NoRemoteEntityCfgFound(Exception):
    pass


class SourceFileDoesNotExist(Exception):
    pass


class ChecksumNotImplemented(Exception):
    pass


class PacketSendNotConfirmed(Exception):
    pass


class CfdpSourceHandler:
    def __init__(
        self,
        cfg: LocalEntityCfg,
        seq_num_provider: ProvidesSeqCount,
        user: CfdpUserBase,
    ):
        self.states = SourceStateWrapper()
        self.cfg = cfg
        self.user = user
        self.params = TransferFieldWrapper(cfg.local_entity_id)
        self.seq_num_provider = seq_num_provider
        self.remote_cfg: Optional[RemoteEntityCfg] = None
        self._request_wrapper = CfdpRequestWrapper(None)
        self._current_req = CfdpRequestType

    def start_transaction(
        self, wrapper: CfdpRequestWrapper, remote_cfg: RemoteEntityCfg
    ):
        if wrapper.request_type == CfdpRequestType.PUT:
            self._current_req = wrapper.request_type
            self.remote_cfg = remote_cfg

    def operation_with_send(self, com_if: ComInterface):
        self.operation()
        self.send_wrapper(com_if)

    def operation(self):
        if self.states.state == SourceState.IDLE:
            return
        elif self.states.transaction == SourceState.BUSY_CLASS_1_NACKED:
            put_req = self._request_wrapper.to_put_request()
            if self.states.transaction == SourceTransactionState.IDLE:
                self.states.transaction = SourceTransactionState.TRANSACTION_START
            if self.states.transaction == SourceTransactionState.TRANSACTION_START:
                if not put_req.cfg.source_file.exists():
                    # TODO: Handle this exception in the handler, reset CFDP state machine
                    raise SourceFileDoesNotExist()
                self.params.file_size = put_req.cfg.source_file.stat().st_size
                if self.remote_cfg is None:
                    # It is actually not specified what to do if there is no remote configuration
                    # for a given destination ID. I will treat this as a configuration error now
                    # and raise an exception
                    raise NoRemoteEntityCfgFound()
                self.params.file_segment_len = self.remote_cfg.max_file_segment_len
                self.params.remote_cfg = self.remote_cfg
                self.params.transaction = TransactionId(
                    source_entity_id=self.cfg.local_entity_id,
                    transaction_seq_num=self._get_next_transfer_seq_num(),
                )
                self.user.transaction_indication(self.params.transaction)
                self.states.transfer_state = SourceTransactionState.CRC_PROCEDURE
            if self.states.transfer_state == SourceTransactionState.CRC_PROCEDURE:
                self.params.fp.crc32 = self.calc_cfdp_file_crc(
                    crc_type=self.remote_cfg.crc_type,
                    file=put_req.cfg.source_file,
                    file_sz=self.params.fp.size,
                    segment_len=self.params.fp.segment_len,
                )

            if self.states.transfer_state == SourceTransactionState.SENDING_METADATA:
                if self.states.packet_ready:
                    raise PacketSendNotConfirmed(
                        f"Must send current packet {self.params.pdu_wrapper.base} first"
                    )
                # TODO: CRC flag is derived from remote entity ID configuration
                # TODO: Determine file size and check whether source file is valid
                self.params.pdu_conf.seg_ctrl = put_req.cfg.seg_ctrl
                self.params.pdu_conf.dest_entity_id = put_req.cfg.destination_id
                self.params.pdu_conf.crc_flag = self.remote_cfg.crc_on_transmission
                self.params.pdu_conf.direction = Direction.TOWARDS_RECEIVER
                self.params.pdu_conf.transaction_seq_num = (
                    self.params.transaction.seq_num
                )
                self.params.pdu_conf.trans_mode = put_req.cfg.trans_mode
                self.params.pdu_wrapper.base = MetadataPdu(
                    pdu_conf=self.params.pdu_conf,
                    file_size=self.params.file_size,
                    source_file_name=put_req.cfg.source_file.as_posix(),
                    dest_file_name=put_req.cfg.dest_file,
                    # TODO: Hardcode this checksum for now. Standard-Conformance requires that this
                    #       is determined by the remote entity configuration
                    checksum_type=self.remote_cfg.crc_type,
                    closure_requested=self.remote_cfg.closure_reuested,
                )
                self.states.transfer_state = SourceTransactionState.SENDING_FILE_DATA
                return
            if self.states.transfer_state == SourceTransactionState.SENDING_FILE_DATA:
                if self._prepare_next_file_data_pdu(put_req):
                    return
            if self.states.transfer_state == SourceTransactionState.SENDING_EOF:
                return self._prepare_eof_pdu()
            if (
                self.states.transfer_state
                == SourceTransactionState.NOTICE_OF_COMPLETION
            ):
                self.user.transaction_finished_indication(
                    transaction_id=self.params.transaction,
                    condition_code=ConditionCode.NO_ERROR,
                    file_status=FileDeliveryStatus.FILE_STATUS_UNREPORTED,
                    delivery_code=DeliveryCode.DATA_COMPLETE,
                )
                self.states.transfer_state = SourceTransactionState.IDLE
                self.states.state = SourceState.IDLE

    def send_wrapper(self, com_if: ComInterface):
        if self.states.state == SourceState.BUSY_CLASS_1_NACKED:
            if self.states.transaction == SourceTransactionState.SENDING_METADATA:
                metadata_pdu = self.params.pdu_wrapper.to_metadata_pdu()
                com_if.send(metadata_pdu.pack())
                self.states.transaction = SourceTransactionState.SENDING_EOF
                return self.confirm_packet_sent()
            if self.states.transaction == SourceTransactionState.SENDING_FILE_DATA:
                file_data_pdu = self.params.pdu_wrapper.to_file_data_pdu()
                com_if.send(file_data_pdu.pack())
                if self.params.fp.offset == self.params.fp.size:
                    self.states.transaction = SourceTransactionState.SENDING_EOF
                return self.confirm_packet_sent()
            if self.states.transaction == SourceTransactionState.SENDING_EOF:
                eof_pdu = self.params.pdu_wrapper.to_eof_pdu()
                com_if.send(eof_pdu.pack())
                self.states.transaction = SourceTransactionState.NOTICE_OF_COMPLETION
                return self.confirm_packet_sent()

    def confirm_packet_sent(self):
        self.states.packet_ready = False

    def advance_state_machine(self):
        if self.states.packet_ready:
            raise PacketSendNotConfirmed(
                f"Must send current packet {self.params.pdu_wrapper.base} before "
                f"advancing state machine"
            )
        if self.states.state == SourceState.BUSY_CLASS_1_NACKED:
            if self.states.transaction == SourceTransactionState.SENDING_METADATA:
                self.states.transaction = SourceTransactionState.SENDING_EOF
            elif self.states.transaction == SourceTransactionState.SENDING_FILE_DATA:
                if self.params.fp.offset == self.params.fp.size:
                    self.states.transaction = SourceTransactionState.SENDING_EOF
            elif self.states.transaction == SourceTransactionState.SENDING_EOF:
                self.states.transaction = SourceTransactionState.NOTICE_OF_COMPLETION

    @classmethod
    def calc_cfdp_file_crc(
        cls, crc_type: ChecksumTypes, file: Path, file_sz: int, segment_len: int
    ):
        if crc_type == ChecksumTypes.CRC_32:
            cls.calc_crc_for_file_crcmod(
                PredefinedCrc("crc32"), file, file_sz, segment_len
            )
        elif crc_type == ChecksumTypes.CRC_32C:
            cls.calc_crc_for_file_crcmod(
                PredefinedCrc("crc32c"), file, file_sz, segment_len
            )
        else:
            raise ChecksumNotImplemented(f"Checksum {crc_type} not implemented")

    @classmethod
    def calc_crc_for_file_crcmod(
        cls, crc_obj: PredefinedCrc, file: Path, file_sz: int, segment_len: int
    ):
        if not file.exists():
            # TODO: Handle this exception in the handler, reset CFDP state machine
            raise SourceFileDoesNotExist()
        current_offset = 0
        # Calculate the file CRC
        with open(file, "rb") as of:
            while True:
                if current_offset == file_sz:
                    break
                next_offset = current_offset + segment_len
                if next_offset > file_sz:
                    read_len = next_offset % file_sz
                else:
                    read_len = segment_len
                if read_len > 0:
                    of.seek(current_offset)
                    crc_obj.update(of.read(read_len))
                current_offset += read_len
            return crc_obj.digest()

    def _prepare_next_file_data_pdu(self, request: PutRequest) -> bool:
        """Prepare the next file data PDU

        :param request:
        :return: True if a packet was prepared, False if PDU handling is done and the next steps
            in the Copy File procedure can be performed
        """
        with open(request.cfg.source_file, "rb") as of:
            next_offset = self.params.fp.offset + self.params.fp.segment_len
            if self.params.fp.offset == self.params.fp.size:
                return False
            if self.states.packet_ready:
                raise PacketSendNotConfirmed(
                    f"Must send current packet {self.params.pdu_wrapper.base} first"
                )
            if next_offset > self.params.fp.size:
                read_len = next_offset % self.params.fp.size
            else:
                read_len = self.params.fp.segment_len
            of.seek(self.params.fp.offset)
            file_data = of.read(read_len)
            self.params.pdu_conf.transaction_seq_num = self._get_next_transfer_seq_num()
            # NOTE: Support for record continuation state not implemented yet. Segment metadata
            #       flag is therefore always set to False
            file_data_pdu = FileDataPdu(
                pdu_conf=self.params.pdu_conf,
                file_data=file_data,
                offset=self.params.fp.offset,
                segment_metadata_flag=False,
            )
            self.params.fp.offset = next_offset
            self.params.pdu_wrapper.base = file_data_pdu
        return True

    def _prepare_eof_pdu(self):
        if self.states.packet_ready:
            raise PacketSendNotConfirmed(
                f"Must send current packet {self.params.pdu_wrapper.base} first"
            )
        self.params.pdu_wrapper.base = EofPdu(
            file_checksum=self.params.fp.crc32,
            file_size=self.params.fp.size,
            pdu_conf=self.params.pdu_conf,
        )

    def _get_next_transfer_seq_num(self) -> UnsignedByteField:
        next_seq_num = self.seq_num_provider.get_and_increment()
        if self.seq_num_provider.max_bit_width == 8:
            return ByteFieldU8(next_seq_num)
        elif self.seq_num_provider.max_bit_width == 16:
            return ByteFieldU16(next_seq_num)
        elif self.seq_num_provider.max_bit_width == 32:
            return ByteFieldU32(next_seq_num)
        else:
            raise ValueError(
                "Invalid bit width for sequence number provider, must be one of [8, 16, 32]"
            )


class CfdpRxHandler:
    pass


class CfdpHandler:
    def __init__(
        self,
        local_cfg: LocalEntityCfg,
        remote_cfg: RemoteEntityTable,
        seq_num_provider: ProvidesSeqCount,
        cfdp_user: CfdpUserBase,
    ):
        """

        :param local_cfg: Local entity configuration
        :param remote_cfg: Configuration table for remote entities
        :param cfdp_user: CFDP user which will receive indication messages and which also contains
            the virtual filestore implementation
        """
        # The ID is going to be constant after initialization, store in separately
        self.id = local_cfg.local_entity_id
        self.cfg = local_cfg
        self.remote_cfg_table = remote_cfg
        self.cfdp_user = cfdp_user
        self._tx_handler = CfdpSourceHandler(self.cfg, seq_num_provider, cfdp_user)
        self.state = StateWrapper(
            state=CfdpStates.IDLE, source_handler_state=self._tx_handler.states
        )
        self._request_wrapper = CfdpRequestWrapper(None)
        self._next_reception_pdu_wrapper = PduWrapper(None)
        self._cfdp_result = CfdpResult()

    def state_machine(self) -> CfdpResult:
        """Perform the CFDP state machine. Primary function to call to generate new PDUs to send
        and to advance the internal state machine which also issues indications to the
        CFDP user.

        :raises SequenceNumberOverflow: Overflow of sequence number occurred. In this case, the
            number will be reset but no operation will occur and the state machine needs
            to be called again
        :raises NoRemoteEntityCfgFound: If no remote entity configuration for a given destination
            ID was found
        """
        if self.state != CfdpStates.IDLE:
            self._handle_transfer_state_machine()
            pass
        return self._cfdp_result

    def _handle_transfer_state_machine(self):
        if self._request_wrapper.request == CfdpRequestType.PUT:
            self._tx_handler.operation()

    def reset_transfer_state(self):
        pass
        # TODO: Implement
        # self.state.transfer_state = SorceState.IDLE
        # self._transfer_params.reset()

    def _prepare_finish_pdu(self):
        # TODO: Implement
        pass

    def pass_packet(self, raw_tm_packet: bytes):
        # TODO: Packet Handler
        pass

    @property
    def transfer_packet_ready(self):
        if self._tx_handler.params.pdu_wrapper.base is not None:
            return True
        return False

    @property
    def reception_packet_ready(self):
        if self._next_reception_pdu_wrapper.base is not None:
            return True
        return False

    @property
    def transfer_packet_wrapper(self) -> PduWrapper:
        """Yield the next packet required to transfer a file"""
        return self._tx_handler.params.pdu_wrapper

    @property
    def reception_packet_wrapper(self) -> PduWrapper:
        """Yield the next packed required to receive a file"""
        return self._next_reception_pdu_wrapper

    def start_put_request(self, put_request: PutRequest):
        """A put request initiates a copy procedure. For now, only one put request at a time
        is allowed"""
        if self.state.source_handler_state != CfdpStates.IDLE:
            raise BusyError(f"Currently in {self.state}, can not handle put request")
        self._request_wrapper.base = put_request
        remote_cfg = self.remote_cfg_table.get_remote_entity(
            put_request.cfg.destination_id
        )
        if remote_cfg is None:
            raise NoRemoteEntityCfgFound()
        self._tx_handler.start_transaction(
            remote_cfg=remote_cfg, wrapper=self._request_wrapper
        )
