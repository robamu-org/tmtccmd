import abc
from typing import List, Optional

from spacepackets.cfdp import ConditionCode, FileStoreResponseTlv
from spacepackets.cfdp.pdu.finished import DeliveryCode, FileDeliveryStatus
from tmtccmd import get_console_logger
from tmtccmd.cfdp.defs import TransactionId
from tmtccmd.cfdp.filestore import VirtualFilestore


LOGGER = get_console_logger()


class CfdpUserBase(abc.ABC):
    def __init__(self, vfs: VirtualFilestore):
        self.vfs = vfs

    @abc.abstractmethod
    def transaction_indication(self, transaction_id: TransactionId):
        """This indication is used to report the transaction ID to the CFDP user"""
        LOGGER.info(f"Transaction indication with ID {transaction_id}")

    @abc.abstractmethod
    def transaction_finished_indication(
        self,
        transaction_id: TransactionId,
        condition_code: ConditionCode,
        file_status: FileDeliveryStatus,
        delivery_code: DeliveryCode,
        _fs_responses: Optional[List[FileStoreResponseTlv]] = None,
        _status_report: Optional[any] = None,
    ):
        LOGGER.info(f"Transaction with ID {transaction_id} finished")
        LOGGER.info(
            f"Condition Code: {condition_code} | File Status: {file_status} | "
            f"Delivery Code: {delivery_code}"
        )

    @abc.abstractmethod
    def eof_sent_indication(self, transaction_id: TransactionId):
        LOGGER.info(f"EOF sent for transaction with ID {transaction_id}")

    @abc.abstractmethod
    def abandon_indication(
        self, transaction_id: int, cond_code: ConditionCode, progress: int
    ):
        LOGGER.warning(
            f"Abandoned transaction with ID {transaction_id}, condition code {cond_code} and "
            f"progress {progress}"
        )
