import enum
import os
import abc
from typing import Optional, Type

from .filestore import VirtualFilestore
from tmtccmd.utility.tmtc_printer import TmTcPrinter
from tmtccmd.utility.logger import get_console_logger
from tmtccmd.com_if.com_interface_base import CommunicationInterface
from spacepackets.cfdp.pdu.metadata import MetadataPdu
from spacepackets.cfdp.conf import PduConfig
from spacepackets.cfdp.definitions import TransmissionModes, ChecksumTypes

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
    ):
        self.cfdp_type = cfdp_type
        self.com_if = com_if
        self.cfdp_user = cfdp_user
        self.__busy = False
        pass

    @property
    def com_if(self):
        return self.__com_if

    @com_if.setter
    def com_if(self, com_if: CommunicationInterface):
        self.__com_if = com_if

    def state_machine(self):
        pass

    def pass_packet(
        self, apid: int, raw_tm_packet: bytearray, tmtc_printer: TmTcPrinter
    ):
        pass

    def put_request(self, cfdp_type: CfdpClass):
        if self.__is_busy():
            # TODO: Custom exception
            return
        if self.cfdp_type != cfdp_type:
            self.cfdp_type = cfdp_type

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

    def __is_busy(self) -> bool:
        return self.__busy
