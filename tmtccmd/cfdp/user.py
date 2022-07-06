import abc

from spacepackets.cfdp import ConditionCode
from tmtccmd import get_console_logger
from tmtccmd.cfdp.filestore import VirtualFilestore


LOGGER = get_console_logger()


class CfdpUserBase(abc.ABC):
    def __init__(self, vfs: VirtualFilestore):
        self.vfs = vfs

    @abc.abstractmethod
    def transaction_indication(self, transaction_id: int):
        """This indication is used to report the transaction ID to the CFDP user"""
        LOGGER.info(f"Transaction indication with ID {transaction_id}")

    @abc.abstractmethod
    def transaction_finished_indication(self, transaction_id: int):
        LOGGER.info(f"Transaction with ID {transaction_id} finished")

    @abc.abstractmethod
    def abandon_indication(
        self, transaction_id: int, cond_code: ConditionCode, progress: int
    ):
        LOGGER.warning(
            f"Abandoned transaction with ID {transaction_id}, condition code {cond_code} and "
            f"progress {progress}"
        )
