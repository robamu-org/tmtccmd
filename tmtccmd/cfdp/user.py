from abc import abstractmethod, ABC
from dataclasses import dataclass
from typing import List, Optional

from spacepackets.cfdp import ConditionCode, FileStoreResponseTlv, MessageToUserTlv
from spacepackets.cfdp.pdu.file_data import RecordContinuationState
from spacepackets.cfdp.pdu.finished import DeliveryCode, FileDeliveryStatus
from spacepackets.util import UnsignedByteField
from tmtccmd.logging import get_console_logger
from tmtccmd.cfdp.defs import TransactionId
from tmtccmd.cfdp.filestore import VirtualFilestore, HostFilestore

LOGGER = get_console_logger()


@dataclass
class MetadataRecvParams:
    transaction_id: TransactionId
    source_id: UnsignedByteField
    file_size: Optional[int]
    source_file_name: Optional[str]
    dest_file_name: Optional[str]
    msgs_to_user: Optional[List[MessageToUserTlv]] = None


@dataclass
class TransactionFinishedParams:
    transaction_id: TransactionId
    condition_code: ConditionCode
    file_status: FileDeliveryStatus
    delivery_code: DeliveryCode
    fs_responses: Optional[List[FileStoreResponseTlv]] = None
    status_report: Optional[any] = None


@dataclass
class FileSegmentRecvdParams:
    """The length of the segment metadata is not supplied as an extra parameter as it can be
    simply queried with len(segment_metadata)
    """

    transaction_id: TransactionId
    offset: int
    length: int
    record_cont_state: Optional[RecordContinuationState]
    segment_metadata: Optional[bytes]


class CfdpUserBase(ABC):
    """This user base class provides the primary user interface to interact with CFDP handlers.
    It is also used to pass the Virtual Filestore (VFS) implementation to the CFDP handlers
    so the filestore operations can be mapped to the underlying filestore.

    This class is used by implementing it in a child class and then passing it to the CFDP
    handler objects. The base class provides default implementation for the user indication
    primitives specified in the CFDP standard. The user can override these implementations
    to provide custom indication handlers.
    """

    def __init__(self, vfs: Optional[VirtualFilestore] = None):
        if vfs is None:
            vfs = HostFilestore()
        self.vfs = vfs

    @abstractmethod
    def transaction_indication(self, transaction_id: TransactionId):
        """This indication is used to report the transaction ID to the CFDP user"""
        LOGGER.info(f"Transaction.indication for {transaction_id}")

    @abstractmethod
    def eof_sent_indication(self, transaction_id: TransactionId):
        LOGGER.info(f"EOF-Sent.indication for {transaction_id}")

    @abstractmethod
    def transaction_finished_indication(self, params: TransactionFinishedParams):
        LOGGER.info(
            f"Transaction-Finished.indication for {params.transaction_id}. Parameters:"
        )
        print(params)

    @abstractmethod
    def metadata_recv_indication(self, params: MetadataRecvParams):
        LOGGER.info(
            f"Metadata-Recv.indication for {params.transaction_id}. Parameters:"
        )
        print(params)

    @abstractmethod
    def file_segment_recv_indication(self, params: FileSegmentRecvdParams):
        LOGGER.info(
            f"File-Segment-Recv.indication for {params.transaction_id}. Parameters:"
        )
        print(params)

    @abstractmethod
    def report_indication(self, transaction_id: TransactionId, status_report: any):
        # TODO: p.28 of the CFDP standard specifies what information the status report parameter
        #       could contain. I think it would be better to not hardcode the type of the status
        #       report here, but something like Union[any, CfdpStatusReport] with CfdpStatusReport
        #       being an implementation which supports all three information suggestions would be
        #       nice
        pass

    @abstractmethod
    def suspended_indication(
        self, transaction_id: TransactionId, cond_code: ConditionCode
    ):
        LOGGER.info(
            f"Suspended.indication for {transaction_id} | Condition Code: {cond_code}"
        )

    @abstractmethod
    def resumed_indication(self, transaction_id: TransactionId, progress: int):
        LOGGER.info(
            f"Resumed.indication for {transaction_id} | Progress: {progress} bytes"
        )

    @abstractmethod
    def fault_indication(
        self, transaction_id: TransactionId, cond_code: ConditionCode, progress: int
    ):
        LOGGER.warning(
            f"Fault.indication for {transaction_id} | Condition Code: {cond_code} | "
            f"Progress: {progress} bytes"
        )

    @abstractmethod
    def abandoned_indication(
        self, transaction_id: TransactionId, cond_code: ConditionCode, progress: int
    ):
        LOGGER.warning(
            f"Abandoned.indication for {transaction_id} | Condition Code: {cond_code} | "
            f"Progress: {progress} bytes"
        )

    @abstractmethod
    def eof_recv_indication(self, transaction_id: TransactionId):
        LOGGER.info(f"EOF-Recv.indication for {transaction_id}")
