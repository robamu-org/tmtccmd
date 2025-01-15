from deprecated.sphinx import deprecated
import logging
from typing import Optional
from abc import abstractmethod, ABC

from prompt_toolkit.history import History

from tmtccmd.util.obj_id import ObjectIdDictT

from tmtccmd.config.tmtc import CmdTreeNode
from tmtccmd.core import BackendBase

from .com import ComCfgBase, ComInterface
from .tmtc import TmtcDefinitionWrapper
from .defs import default_json_path, CORE_COM_IF_DICT, ComIfMapping


_LOGGER = logging.getLogger(__name__)


class HookBase(ABC):
    """This hook allows users to adapt the TMTC commander core to the unique mission requirements.
    It is used by implementing all abstract functions and then passing the instance to the
    TMTC commander core.
    """

    def __init__(self, cfg_file_path: Optional[str] = None):
        self.cfg_path = cfg_file_path
        if self.cfg_path is None:
            self.cfg_path = default_json_path()

    @abstractmethod
    def get_communication_interface(self, com_if_key: str) -> Optional[ComInterface]:
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

    def get_cmd_history(self) -> Optional[History]:
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

    @deprecated(version="8.0.0", reason="application specific code")
    def get_object_ids(self) -> ObjectIdDictT:
        from tmtccmd.config.objects import get_base_component_id_mapping

        """The user can specify an object ID dictionary here mapping object ID bytearrays to a
        list. This list could contain containing the string representation or additional
        information about that object ID.
        """
        return get_base_component_id_mapping()

    @deprecated(
        version="8.0.0rc0",
        reason="implement and use get_command_definitions instead",
    )
    def get_tmtc_definitions(self) -> TmtcDefinitionWrapper:
        """This is a dicitonary mapping services represented by strings to an operation code
        dictionary.

        :return:
        """
        from tmtccmd.config.globals import get_default_tmtc_defs

        return get_default_tmtc_defs()

    @deprecated(
        version="8.0.0rc0",
        reason="implement and use get_communication_interface instead",
    )
    def assign_communication_interface(self, com_if_key: str) -> Optional[ComInterface]:
        """Assign the communication interface used by the TMTC commander to send and receive
        TMTC with.

        :param com_if_key:      String key of the communication interface to be created.
        """
        return self.get_communication_interface(com_if_key)
