import dataclasses
import struct
from pathlib import Path
from typing import Optional
from crcmod.predefined import PredefinedCrc

from spacepackets.cfdp.pdu import PduWrapper, EofPdu
from spacepackets.cfdp.pdu.file_data import FileDataPdu
from tmtccmd.logging import get_console_logger

from spacepackets.cfdp.pdu.metadata import MetadataPdu
from spacepackets.cfdp.conf import PduConfig
from spacepackets.cfdp.defs import (
    ChecksumTypes,
    Direction,
)
from .defs import (
    CfdpStates,
    SequenceNumberOverflow,
    BusyError,
    CfdpRequest,
    CfdpStateWrapper,
    CfdpTransferState,
)
from .mib import LocalEntityCfg, RemoteEntityTable, RemoteEntityCfg
from .request import CfdpRequestWrapper, PutRequest
from .user import CfdpUserBase


LOGGER = get_console_logger()


class CfdpHandlerRequest:
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
    def __init__(self, local_entity_id: bytes):
        self.pdu_wrapper = PduWrapper(None)
        self.fp = FileParams()
        self.seq_num = 0
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


class CfdpHandler:
    def __init__(
        self,
        local_cfg: LocalEntityCfg,
        remote_cfg: RemoteEntityTable,
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
        self.state = CfdpStateWrapper(
            state=CfdpStates.IDLE, transfer_state=CfdpTransferState.IDLE
        )

        self._request_wrapper = CfdpRequestWrapper(None)
        self._transfer_params = TransferFieldWrapper(self.cfg.local_entity_id)
        self._next_reception_pdu_wrapper = PduWrapper(None)

        self._cfdp_handler_request = CfdpHandlerRequest()

    def state_machine(self) -> CfdpHandlerRequest:
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
        return self._cfdp_handler_request

    def _handle_transfer_state_machine(self):
        if self._request_wrapper.request == CfdpRequest.PUT:
            self._handle_put_request()

    def _handle_put_request(self):
        request = self._request_wrapper.to_put_request()
        if self.state.transfer_state == CfdpTransferState.INITIALIZE:
            if not request.cfg.source_file.exists():
                # TODO: Handle this exception in the handler, reset CFDP state machine
                raise SourceFileDoesNotExist()
            self._transfer_params.file_size = request.cfg.source_file.stat().st_size
            remote_cfg = self.remote_cfg_table.get_remote_entity(
                request.cfg.destination_id
            )
            if remote_cfg is None:
                # It is actually not specified what to do if there is no remote configuration
                # for a given destination ID. I will treat this as a configuration error now
                # and raise an exception
                raise NoRemoteEntityCfgFound()
            self._transfer_params.file_segment_len = remote_cfg.max_file_segment_len
            self._transfer_params.remote_cfg = remote_cfg
            self.state.transfer_state = CfdpTransferState.CRC_PROCEDURE
        if self.state.transfer_state == CfdpTransferState.CRC_PROCEDURE:
            self._transfer_params.fp.crc32 = self.calc_cfdp_file_crc(
                crc_type=self._transfer_params.remote_cfg.crc_type,
                file=request.cfg.source_file,
                file_sz=self._transfer_params.file_size,
                segment_len=self._transfer_params.file_segment_len,
            )
            self.state.transfer_state = CfdpTransferState.SENDING_METADATA
        if self.state.transfer_state == CfdpTransferState.SENDING_METADATA:
            # TODO: CRC flag is derived from remote entity ID configuration
            # TODO: Determine file size and check whether source file is valid
            self._transfer_params.pdu_conf.seg_ctrl = request.cfg.seg_ctrl
            self._transfer_params.pdu_conf.dest_entity_id = request.cfg.destination_id
            self._transfer_params.pdu_conf.crc_flag = (
                self._transfer_params.remote_cfg.crc_on_transmission
            )
            self._transfer_params.pdu_conf.direction = Direction.TOWARDS_RECEIVER
            self._transfer_params.pdu_conf.transaction_seq_num = 0
            self._transfer_params.pdu_conf.trans_mode = request.cfg.trans_mode
            self._next_reception_pdu_wrapper.base = MetadataPdu(
                pdu_conf=self._transfer_params.pdu_conf,
                file_size=self._transfer_params.file_size,
                source_file_name=request.cfg.source_file.as_posix(),
                dest_file_name=request.cfg.dest_file,
                # TODO: Hardcode this checksum for now. Standard-Conformance requires that this
                #       is determined by the remote entity configuration
                checksum_type=self._transfer_params.remote_cfg.crc_type,
                # TODO: Likewise: This is probably some sort of managed parameter
                closure_requested=False,
            )
            self.state = CfdpTransferState.SENDING_FILE_DATA
            return
        if self.state == CfdpTransferState.SENDING_FILE_DATA:
            if self._prepare_next_file_data_pdu(request):
                return
        if self.state == CfdpTransferState.SENDING_EOF:
            return self._prepare_eof_pdu()

    def reset_transfer_state(self):
        self.state.transfer_state = CfdpTransferState.IDLE
        self._transfer_params.reset()

    def _prepare_next_file_data_pdu(self, request: PutRequest) -> bool:
        """Prepare the next file data PDU

        :param request:
        :return: True if a packet was prepared, False if PDU handling is done and the next steps
            in the Copy File procedure can be performed
        """
        with open(request.cfg.source_file, "rb") as of:
            next_offset = (
                self._transfer_params.file_offset + self._transfer_params.fp.segment_len
            )
            if self._transfer_params.file_offset == self._transfer_params.fp.size:
                self.state = CfdpTransferState.SENDING_EOF
                return False
            if next_offset > self._transfer_params.fp.size:
                read_len = next_offset % self._transfer_params.fp.size
            else:
                read_len = self._transfer_params.fp.segment_len
            of.seek(self._transfer_params.file_offset)
            file_data = of.read(read_len)
            self._transfer_params.pdu_conf.transaction_seq_num = (
                self._get_next_transfer_seq_num()
            )
            # NOTE: Support for record continuation state not implemented yet. Segment metadata
            #       flag is therefore always set to False
            file_data_pdu = FileDataPdu(
                pdu_conf=self._transfer_params.pdu_conf,
                file_data=file_data,
                offset=self._transfer_params.file_offset,
                segment_metadata_flag=False,
            )
            self._transfer_params.file_offset = next_offset
            self._transfer_params.pdu_wrapper.base = file_data_pdu
        return True

    def _prepare_eof_pdu(self):
        self._transfer_params.pdu_wrapper.base = EofPdu(
            file_checksum=self._transfer_params.fp.crc32,
            file_size=self._transfer_params.fp.size,
            pdu_conf=self._transfer_params.pdu_conf,
        )
        pass

    def _prepare_finish_pdu(self):
        # TODO: Implement
        pass

    def _get_next_transfer_seq_num(self) -> bytes:
        seq_num_raw = bytes()
        if self.cfg.length_seq_num == 1:
            if self._transfer_params.seq_num >= pow(2, 8) - 1:
                raise SequenceNumberOverflow(
                    "8-bit transaction sequence number overflowed"
                )
            seq_num_raw = bytes([self._transfer_params.seq_num])
        elif self.cfg.length_seq_num == 2:
            if self._transfer_params.seq_num == pow(2, 16) - 1:
                raise SequenceNumberOverflow(
                    "16-bit transaction sequence number overflowed"
                )
            seq_num_raw = struct.pack("!H", self._transfer_params.seq_num)
        elif self.cfg.length_seq_num == 4:
            if self._transfer_params.seq_num == pow(2, 32) - 1:
                raise SequenceNumberOverflow(
                    "32-bit transaction sequence number overflowed"
                )
            seq_num_raw = struct.pack("!I", self._transfer_params.seq_num)
        self._transfer_params.seq_num += 1
        return seq_num_raw

    def pass_packet(self, raw_tm_packet: bytes):
        # TODO: Packet Handler
        pass

    @property
    def transfer_packet_ready(self):
        if self._transfer_params.pdu_wrapper.base is not None:
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
        return self._transfer_params.pdu_wrapper

    @property
    def reception_packet_wrapper(self) -> PduWrapper:
        """Yield the next packed required to receive a file"""
        return self._next_reception_pdu_wrapper

    def put_request(self, put_request: PutRequest):
        """A put request initiates a copy procedure. For now, only one put request at a time
        is allowed"""
        if self.state != CfdpStates.IDLE:
            raise BusyError(f"Currently in {self.state}, can not handle put request")
        self._request_wrapper = put_request
        self.state.transfer_state = CfdpTransferState.CRC_PROCEDURE

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
