import enum
import os
import abc
from typing import Optional, Type, List

from .filestore import VirtualFilestore
from tmtccmd.utility.tmtc_printer import TmTcPrinter
from tmtccmd.utility.logger import get_console_logger
from tmtccmd.com_if.com_interface_base import CommunicationInterface
from spacepackets.cfdp.pdu.metadata import MetadataPdu
from spacepackets.cfdp.conf import PduConfig
from spacepackets.cfdp.definitions import (
    TransmissionModes,
    ChecksumTypes,
    SegmentationControl,
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


class CfdpClass(enum.Enum):
    UNRELIABLE_CL1 = 0
    RELIABLE_CL2 = 1


class PutRequest:
    destination_id: bytes
    source_file_name: str
    dest_file_name: str
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


class BusyError(Exception):
    pass


class CfdpUserBase:
    def __init__(self, vfs: Type[VirtualFilestore]):
        self.vfs = vfs

    @abc.abstractmethod
    def transaction_indication(self, code: CfdpIndication):
        LOGGER.info(f"Received transaction indication {code}")


class CfdpHandler:
    def __init__(
        self,
        com_if: Optional[CommunicationInterface],
        cfdp_type: Optional[CfdpClass],
        cfdp_user: Type[CfdpUserBase],
        send_interval: float,
    ):
        self.cfdp_type = cfdp_type
        self.com_if = com_if
        self.cfdp_user = cfdp_user
        self.state = CfdpStates.IDLE
        self.send_interval = send_interval

        self.__current_put_request: Optional[PutRequest] = None

    @property
    def com_if(self):
        return self.__com_if

    @com_if.setter
    def com_if(self, com_if: CommunicationInterface):
        self.__com_if = com_if

    def state_machine(self):
        if self.state != CfdpStates.IDLE:
            if self.state == CfdpStates.CRC_PROCEDURE:
                # Skip this step for now
                self.state = CfdpStates.SENDING_METADATA
            if self.state == CfdpStates.SENDING_METADATA:
                self.state = CfdpStates.SENDING_FILE_DATA_PDUS
            pass

    def pass_packet(
        self, apid: int, raw_tm_packet: bytearray, tmtc_printer: TmTcPrinter
    ):
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
        file_repository: str,
        file_name: str,
        dest_repository: str,
        dest_name: str,
    ):
        if self.cfdp_type == CfdpClass.RELIABLE_CL2:
            pdu_conf.trans_mode = TransmissionModes.ACKNOWLEDGED
        else:
            pdu_conf.trans_mode = TransmissionModes.UNACKNOWLEDGED
        source_file = os.path.join(file_repository, file_name)
        dest_file = os.path.join(dest_repository, dest_name)
        metadata_pdu = MetadataPdu(
            pdu_conf=pdu_conf,
            file_size=0,
            source_file_name=source_file,
            dest_file_name=dest_file,
            checksum_type=ChecksumTypes.NULL_CHECKSUM,
            closure_requested=False,
        )
        data = metadata_pdu.pack()
        self.com_if.send(data=data)
