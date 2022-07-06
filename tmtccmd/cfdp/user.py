import abc

from tmtccmd import get_console_logger
from tmtccmd.cfdp.defs import CfdpIndication
from tmtccmd.cfdp.filestore import VirtualFilestore


LOGGER = get_console_logger()


class CfdpUserBase(abc.ABC):
    def __init__(self, vfs: VirtualFilestore):
        self.vfs = vfs

    @abc.abstractmethod
    def transaction_indication(self, code: CfdpIndication):
        LOGGER.info(f"Received transaction indication {code}")
