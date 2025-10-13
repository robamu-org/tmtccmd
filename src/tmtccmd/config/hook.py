import logging
from abc import ABC, abstractmethod

from prompt_toolkit.history import History

from tmtccmd.config.tmtc import CmdTreeNode
from tmtccmd.core import BackendBase

from .com import ComCfgBase, ComInterface
from .defs import CORE_COM_IF_DICT, ComIfMapping, default_json_path

_LOGGER = logging.getLogger(__name__)


class HookBase(ABC):
    """This hook allows users to adapt the TMTC commander core to the unique mission requirements.
    It is used by implementing all abstract functions and then passing the instance to the
    TMTC commander core.
    """

    def __init__(self, cfg_file_path: str | None = None):
        self.cfg_path = cfg_file_path
        if self.cfg_path is None:
            self.cfg_path = default_json_path()

    @abstractmethod
    def get_communication_interface(self, com_if_key: str) -> ComInterface | None:
        from tmtccmd.config.com import create_com_interface_default

        assert self.cfg_path is not None
        cfg_base = ComCfgBase(com_if_key=com_if_key, json_cfg_path=self.cfg_path)
        return create_com_interface_default(cfg_base)

    @abstractmethod
    def get_command_definitions(self) -> CmdTreeNode:
        """This function should return the root node of the command definition tree."""
        pass

    def get_com_if_dict(self) -> ComIfMapping:
        return CORE_COM_IF_DICT

    def get_cmd_history(self) -> History | None:
        """Optionlly return a history class for the past command paths which will be used
        when prompting a command path from the user in CLI mode."""
        return None

    def perform_mode_operation(self, tmtc_backend: BackendBase, mode: int):
        """Perform custom mode operations.

        :param tmtc_backend:
        :param mode:
        :return:
        """
        _LOGGER.warning("No custom mode operation implemented")
