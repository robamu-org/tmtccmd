import enum
import abc
import struct
from typing import Optional, List

from .filestore import VirtualFilestore
from .mib import LocalEntityCfg
from tmtccmd.logging import get_console_logger
from tmtccmd.com_if import ComInterface
from spacepackets.cfdp.pdu.metadata import MetadataPdu
from spacepackets.cfdp.conf import PduConfig
from spacepackets.cfdp.definitions import (
    TransmissionModes,
    ChecksumTypes,
    SegmentationControl,
    Direction,
    CrcFlag,
    FileSize,
)
from spacepackets.cfdp.tlv import (
    FaultHandlerOverrideTlv,
    FlowLabelTlv,
    MessageToUserTlv,
    FileStoreRequestTlv,
)

LOGGER = get_console_logger()


class CfdpRequest(enum.Enum):
    PUT = 0
    REPORT = 1
    CANCEL = 2
    SUSPEND = 3
    RESUME = 4


class CfdpIndication(enum.Enum):
    TRANSACTION = 0
    EOF = 1
    FINISHED = 2
    METADATA = 3
    FILE_SEGMENT_RECV = 4
    REPORT = 5
    SUSPENDED = 6
    RESUMED = 7
    FAULT = 8
    ABANDONED = 9
    EOF_RECV = 10


class PutRequest:
    destination_id: bytes
    source_file: str
    dest_file: str
    seg_ctrl: SegmentationControl
    fault_handler_overrides: Optional[FaultHandlerOverrideTlv] = None
    flow_label_tlv: Optional[FlowLabelTlv] = None
    trans_mode: TransmissionModes
    closure_requested: bool
    msgs_to_user: Optional[List[MessageToUserTlv]] = None
    fs_requests: Optional[List[FileStoreRequestTlv]] = None


class CfdpStates(enum.Enum):
    IDLE = 0
    CRC_PROCEDURE = 1
    SENDING_METADATA = 2
    SENDING_FILE_DATA_PDUS = 3
    SENDING_EOF_DATA_PDU = 4
    SENDING_FINISH_PDU = 5
    SEND_ACK_PDU = 6


class ByteFlowControl:
    period: float
    max_bytes: int


class BusyError(Exception):
    pass


class SequenceNumberOverflow(Exception):
    pass


class CfdpUserBase:
    def __init__(self, vfs: VirtualFilestore):
        self.vfs = vfs

    @abc.abstractmethod
    def transaction_indication(self, code: CfdpIndication):
        LOGGER.info(f"Received transaction indication {code}")


class CfdpHandler:
    def __init__(
        self,
        cfg: LocalEntityCfg,
        com_if: Optional[ComInterface],
        cfdp_user: CfdpUserBase,
        byte_flow_ctrl: ByteFlowControl,
    ):
        """

        :param cfg: Local entity configuration
        :param com_if: Communication interface used to send messages
        :param cfdp_user: CFDP user which will receive indication messages and which also contains
            the virtual filestore implementation
        :param byte_flow_ctrl: Controls the number of bytes sent in a certain interval
            The state machine will only send packets if the maximum number of specified bytes
            is not exceeded in the specified time interval
        """
        # The ID is going to be constant after initialization, store in separately
        self.id = cfg.local_entity_id
        self.cfg = cfg
        self.com_if = com_if
        self.cfdp_user = cfdp_user
        self.state = CfdpStates.IDLE
        self.seq_num = 0
        self.byte_flow_ctrl = byte_flow_ctrl

        self.__current_put_request: Optional[PutRequest] = None

    @property
    def com_if(self):
        return self.__com_if

    @com_if.setter
    def com_if(self, com_if: ComInterface):
        self.__com_if = com_if

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
                    file_size=FileSize.GLOBAL_CONFIG,
                    trans_mode=self.__current_put_request.trans_mode,
                )
                self.send_metadata_pdu(
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
                LOGGER.warning("8-bit transaction sequence number overflowed!")
                self.seq_num = 0
                raise SequenceNumberOverflow
            self.seq_num += 1
            return bytes([self.seq_num])
        elif self.cfg.length_seq_num == 2:
            if self.seq_num == pow(2, 16) - 1:
                LOGGER.warning("16-bit transaction sequence number overflowed!")
                self.seq_num = 0
                raise SequenceNumberOverflow
            return struct.pack("!H", self.seq_num)
        elif self.cfg.length_seq_num == 4:
            if self.seq_num == pow(2, 32) - 1:
                LOGGER.warning("32-bit transaction sequence number overflowed!")
                self.seq_num = 0
                raise SequenceNumberOverflow
            return struct.pack("!I", self.seq_num)

    def pass_packet(self, raw_tm_packet: bytes):
        pass

    def put_request(self, put_request: PutRequest):
        """A put request initiates a copy procedure. For now, only one put request at a time
        is allowed"""
        if self.state != CfdpStates.IDLE:
            raise BusyError
        self.__current_put_request = put_request
        self.state = CfdpStates.CRC_PROCEDURE

    def send_metadata_pdu(
        self,
        pdu_conf: PduConfig,
        source_file: str,
        dest_file: str,
        closure_requested: bool,
    ):
        metadata_pdu = MetadataPdu(
            pdu_conf=pdu_conf,
            file_size=0,
            source_file_name=source_file,
            dest_file_name=dest_file,
            checksum_type=ChecksumTypes.NULL_CHECKSUM,
            closure_requested=closure_requested,
        )
        data = metadata_pdu.pack()
        self.com_if.send(data=data)
