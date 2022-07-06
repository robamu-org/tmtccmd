import struct
from pathlib import Path
from typing import Optional

from .defs import CfdpStates, PutRequest, SequenceNumberOverflow, BusyError
from .mib import LocalEntityCfg
from tmtccmd.logging import get_console_logger
from spacepackets.cfdp.pdu.metadata import MetadataPdu
from spacepackets.cfdp.conf import PduConfig
from spacepackets.cfdp.defs import (
    ChecksumTypes,
    Direction,
    CrcFlag,
    LargeFileFlag,
)
from .user import CfdpUserBase

LOGGER = get_console_logger()


class CfdpHandler:
    def __init__(
        self,
        cfg: LocalEntityCfg,
        cfdp_user: CfdpUserBase,
    ):
        """

        :param cfg: Local entity configuration
        :param cfdp_user: CFDP user which will receive indication messages and which also contains
            the virtual filestore implementation
        """
        # The ID is going to be constant after initialization, store in separately
        self.id = cfg.local_entity_id
        self.cfg = cfg
        self.cfdp_user = cfdp_user
        self.state = CfdpStates.IDLE
        self.seq_num = 0

        self.__current_put_request: Optional[PutRequest] = None

    def state_machine(self):
        """Perform the CFDP state machine

        :raises SequenceNumberOverflow: Overflow of sequence number occured. In this case, the
            number will be reset but no operation will occured and the state machine needs
            to be called again
        """
        if self.state != CfdpStates.IDLE:
            if self.state == CfdpStates.CRC_PROCEDURE:
                # Skip this step for now
                self.state = CfdpStates.SENDING_METADATA
            if self.state == CfdpStates.SENDING_METADATA:
                # TODO: CRC flag is derived from remote entity ID configuration
                # TODO: Determine file size and check whether source file is valid
                pdu_conf = PduConfig(
                    seg_ctrl=self.__current_put_request.seg_ctrl,
                    dest_entity_id=self.__current_put_request.destination_id,
                    source_entity_id=self.id,
                    crc_flag=CrcFlag.GLOBAL_CONFIG,
                    direction=Direction.TOWARDS_RECEIVER,
                    transaction_seq_num=self.__get_next_seq_num(),
                    file_size=LargeFileFlag.GLOBAL_CONFIG,
                    trans_mode=self.__current_put_request.trans_mode,
                )
                self.create_metadata_pdu(
                    pdu_conf=pdu_conf,
                    dest_file=self.__current_put_request.dest_file,
                    source_file=self.__current_put_request.source_file,
                    closure_requested=False,
                )
                self.state = CfdpStates.SENDING_FILE_DATA_PDUS
            pass

    def __get_next_seq_num(self) -> bytes:
        if self.cfg.length_seq_num == 1:
            if self.seq_num == pow(2, 8) - 1:
                self.seq_num = 0
                raise SequenceNumberOverflow(
                    "8-bit transaction sequence number overflowed"
                )
            self.seq_num += 1
            return bytes([self.seq_num])
        elif self.cfg.length_seq_num == 2:
            if self.seq_num == pow(2, 16) - 1:
                self.seq_num = 0
                raise SequenceNumberOverflow(
                    "16-bit transaction sequence number overflowed"
                )
            return struct.pack("!H", self.seq_num)
        elif self.cfg.length_seq_num == 4:
            if self.seq_num == pow(2, 32) - 1:
                self.seq_num = 0
                raise SequenceNumberOverflow(
                    "32-bit transaction sequence number overflowed"
                )
            return struct.pack("!I", self.seq_num)

    def pass_packet(self, raw_tm_packet: bytes):
        # TODO: Packet Handler
        pass

    def yield_next_packet(self):
        pass

    def put_request(self, put_request: PutRequest):
        """A put request initiates a copy procedure. For now, only one put request at a time
        is allowed"""
        if self.state != CfdpStates.IDLE:
            raise BusyError
        self.__current_put_request = put_request
        self.state = CfdpStates.CRC_PROCEDURE

    def create_metadata_pdu(
        self,
        pdu_conf: PduConfig,
        source_file: Path,
        dest_file: str,
        closure_requested: bool,
    ):
        return MetadataPdu(
            pdu_conf=pdu_conf,
            file_size=0,
            source_file_name=source_file.as_posix(),
            dest_file_name=dest_file,
            checksum_type=ChecksumTypes.NULL_CHECKSUM,
            closure_requested=closure_requested,
        )
