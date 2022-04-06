import sys
import argparse
from abc import abstractmethod
from typing import Optional, Union

from tmtccmd.config.definitions import (
    ServiceOpCodeDictT,
    DataReplyUnpacked,
    default_json_path,
)
from tmtccmd.logging import get_console_logger
from tmtccmd.utility.retval import RetvalDictT
from tmtccmd.pus.obj_id import ObjectIdDictT
from tmtccmd.core.backend import BackendBase
from tmtccmd.tc.definitions import TcQueueT
from tmtccmd.com_if.com_interface_base import CommunicationInterface

LOGGER = get_console_logger()


class TmTcHookBase:
    """This hook allows users to adapt the TMTC commander core to the unique mission requirements.
    It is used by implementing all abstract functions and then passing the instance to the
    TMTC commander core.
    """

    def __init__(self, json_cfg_path: Optional[str] = None):
        self.json_cfg_path = json_cfg_path
        if self.json_cfg_path is None:
            self.json_cfg_path = default_json_path()

    @abstractmethod
    def get_object_ids(self) -> ObjectIdDictT:
        from tmtccmd.config.objects import get_core_object_ids

        """The user can specify an object ID dictionary here mapping object ID bytearrays to a
        list. This list could contain containing the string representation or additional
        information about that object ID.
        """
        return get_core_object_ids()

    @abstractmethod
    def assign_communication_interface(
        self, com_if_key: str
    ) -> Optional[CommunicationInterface]:
        """Assign the communication interface used by the TMTC commander to send and receive
        TMTC with.

        :param com_if_key:      String key of the communication interface to be created.
        """
        from tmtccmd.config.com_if import create_communication_interface_default

        return create_communication_interface_default(
            com_if_key=com_if_key, json_cfg_path=self.json_cfg_path
        )

    @abstractmethod
    def get_service_op_code_dictionary(self) -> ServiceOpCodeDictT:
        """This is a dicitonary mapping services represented by strings to an operation code
        dictionary.

        :return:
        """
        from tmtccmd.config.globals import get_default_service_op_code_dict

        return get_default_service_op_code_dict()

    @abstractmethod
    def perform_mode_operation(self, tmtc_backend: BackendBase, mode: int):
        """Perform custom mode operations
        :param tmtc_backend:
        :param mode:
        :return:
        """
        pass

    @abstractmethod
    def pack_service_queue(
        self, service: Union[int, str], op_code: str, service_queue: TcQueueT
    ):
        """Overriding this function allows the user to package a telecommand queue for a given
        service and operation code combination.

        :param service:
        :param op_code:
        :param service_queue:
        :return:
        """
        pass

    @staticmethod
    def handle_service_8_telemetry(
        object_id: bytes, action_id: int, custom_data: bytearray
    ) -> DataReplyUnpacked:
        """This function is called by the TMTC core to handle Service 8 packets
        The user can return a tuple of two lists, where the first list
        is a list of header strings to print and the second list is a list of values to print.
        The TMTC core will take care of printing both lists and logging them.

        :param object_id: Byte representation of the object ID
        :param action_id:
        :param custom_data:
        :return:
        """
        LOGGER.info(
            "TmTcHookBase: No service 8 handling implemented yet in handle_service_8_telemetry "
            "hook function"
        )
        return DataReplyUnpacked()

    def get_retval_dict(self) -> RetvalDictT:
        LOGGER.info("No return value dictionary specified")
        return dict()


def get_global_hook_obj() -> Optional[TmTcHookBase]:
    """This function can be used to get the handle to the global hook object.
    :return:
    """
    try:
        from tmtccmd.core.globals_manager import get_global
        from tmtccmd.config.definitions import CoreGlobalIds

        from typing import cast

        hook_obj_raw = get_global(CoreGlobalIds.TMTC_HOOK)
        if hook_obj_raw is None:
            LOGGER.error("Hook object is invalid!")
            return None
        return cast(TmTcHookBase, hook_obj_raw)
    except ImportError:
        LOGGER.exception("Issues importing modules to get global hook handle!")
        return None
    except AttributeError:
        LOGGER.exception("Attribute error when trying to get global hook handle!")
        return None
