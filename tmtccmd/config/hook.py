from typing import Optional
from abc import abstractmethod, ABC

from tmtccmd.util.obj_id import ObjectIdDictT

from tmtccmd.core import BackendBase
from tmtccmd.util.retval import RetvalDictT

from .com import ComCfgBase, ComInterface
from .tmtc import TmtcDefinitionWrapper
from .defs import default_json_path, CORE_COM_IF_DICT, ComIfDictT


class HookBase(ABC):
    """This hook allows users to adapt the TMTC commander core to the unique mission requirements.
    It is used by implementing all abstract functions and then passing the instance to the
    TMTC commander core.
    """

    def __init__(self, json_cfg_path: Optional[str] = None):
        self.cfg_path = json_cfg_path
        if self.cfg_path is None:
            self.cfg_path = default_json_path()

    @abstractmethod
    def get_object_ids(self) -> ObjectIdDictT:
        from tmtccmd.config.objects import get_core_object_ids

        """The user can specify an object ID dictionary here mapping object ID bytearrays to a
        list. This list could contain containing the string representation or additional
        information about that object ID.
        """
        return get_core_object_ids()

    @abstractmethod
    def assign_communication_interface(self, com_if_key: str) -> Optional[ComInterface]:
        """Assign the communication interface used by the TMTC commander to send and receive
        TMTC with.

        :param com_if_key:      String key of the communication interface to be created.
        """
        from tmtccmd.config.com import create_com_interface_default

        cfg_base = ComCfgBase(com_if_key=com_if_key, json_cfg_path=self.cfg_path)
        return create_com_interface_default(cfg_base)

    def get_com_if_dict(self) -> ComIfDictT:
        return CORE_COM_IF_DICT

    @abstractmethod
    def get_tmtc_definitions(self) -> TmtcDefinitionWrapper:
        """This is a dicitonary mapping services represented by strings to an operation code
        dictionary.

        :return:
        """
        from tmtccmd.config.globals import get_default_tmtc_defs

        return get_default_tmtc_defs()

    def perform_mode_operation(self, tmtc_backend: BackendBase, mode: int):
        """Perform custom mode operations.

        :param tmtc_backend:
        :param mode:
        :return:
        """
        print("No custom mode operation implemented")

    def get_retval_dict(self) -> RetvalDictT:
        from tmtccmd import get_console_logger

        logger = get_console_logger()
        logger.info("No return value dictionary specified")
        return dict()
