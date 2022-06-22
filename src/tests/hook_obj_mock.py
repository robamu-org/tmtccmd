from abc import abstractmethod
from typing import Dict, Union, Optional, Tuple
from unittest.mock import MagicMock
import argparse

from tmtccmd.utility.tmtc_printer import FsfwTmTcPrinter
from tmtccmd.config.com_if import CommunicationInterface
from tmtccmd.config.definitions import DEFAULT_APID
from tmtccmd.config.definitions import ServiceOpCodeDictT, CoreModeList
from tmtccmd.tm.pus_3_hk_base import Service3Base
from tmtccmd.core.ccsds_backend import CcsdsTmtcBackend
from tmtccmd.tc.definitions import QueueHelper
from tmtccmd.config.cfg_hook import TmTcCfgHookBase
from tmtccmd.logging import get_console_logger

LOGGER = get_console_logger()


def create_hook_mock() -> TmTcCfgHookBase:
    """Create simple minimal hook mock using the MagicMock facilities by unittest
    :return:
    """
    tmtc_hook_base = TmTcCfgHookBase()
    tmtc_hook_base.add_globals_pre_args_parsing = MagicMock(return_value=0)
    tmtc_hook_base.add_globals_post_args_parsing = MagicMock(return_value=0)
    tmtc_hook_base.custom_args_parsing = MagicMock(
        return_value=argparse.Namespace(service=17, mode=CoreModeList.IDLE)
    )
    return tmtc_hook_base


def create_hook_mock_with_srv_handlers() -> TmTcCfgHookBase:
    tmtc_hook_base = create_hook_mock()
    tmtc_hook_base.handle_service_8_telemetry = MagicMock(return_value=(["Test"], [0]))
    # Valid returnvalue for now
    srv_3_return_tuple = (["Test"], [0], bytearray(0b10000000), 1)
    tmtc_hook_base.handle_service_3_housekeeping = MagicMock(
        return_value=srv_3_return_tuple
    )
    return tmtc_hook_base


class TestHookObj(TmTcCfgHookBase):
    service_8_handler_called = False
    service_5_handler_called = False
    service_3_handler_called = False

    def __init__(self):
        super(self, TmTcCfgHookBase).__init__()
        self.get_obj_id_called = False
        self.add_globals_pre_args_parsing_called = False
        self.add_globals_post_args_parsing_called = False
        self.assign_communication_interface_called = False

    @abstractmethod
    def get_object_ids(self) -> Dict[bytes, list]:
        """The user can specify an object ID dictionary here mapping object ID bytearrays to a
        list. This list could contain containing the string representation or additional
        information about that object ID.
        """
        return TmTcCfgHookBase.get_object_ids()

    @abstractmethod
    def add_globals_pre_args_parsing(self, gui: bool = False):
        """Add all global variables prior to parsing the CLI arguments.

        :param gui: Set to true if the GUI mode is used
        :return:
        """
        from tmtccmd.config.globals import set_default_globals_pre_args_parsing

        set_default_globals_pre_args_parsing(gui=gui, apid=DEFAULT_APID)

    @abstractmethod
    def add_globals_post_args_parsing(self, args: argparse.Namespace):
        """Add global variables prior after parsing the CLI arguments.

        :param args: Specify whether a GUI is used
        """
        from tmtccmd.config.globals import set_default_globals_post_args_parsing

        set_default_globals_post_args_parsing(
            args=args, json_cfg_path=self.get_json_config_file_path()
        )

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
            com_if_key=com_if_key,
            json_cfg_path=self.get_json_config_file_path(),
        )

    @abstractmethod
    def get_tmtc_definitions(self) -> ServiceOpCodeDictT:
        """This is a dicitonary mapping services represented by strings to an operation code
        dictionary.

        :return:
        """
        from tmtccmd.config.globals import get_default_tmtc_defs

        return get_default_tmtc_defs()

    @abstractmethod
    def perform_mode_operation(self, tmtc_backend: CcsdsTmtcBackend, mode: int):
        """Perform custom mode operations
        :param tmtc_backend:
        :param mode:
        :return:
        """
        pass

    @abstractmethod
    def pack_service_queue(
        self, service: Union[int, str], op_code: str, tc_queue: QueueHelper
    ):
        """Overriding this function allows the user to package a telecommand queue for a given
        service and operation code combination.

        :param service:
        :param op_code:
        :param tc_queue:
        :return:
        """
        pass

    @staticmethod
    def handle_service_8_telemetry(
        object_id: bytes, action_id: int, custom_data: bytearray
    ) -> Tuple[list, list]:
        """This function is called by the TMTC core to handle Service 8 packets
        The user can return a tuple of two lists, where the first list
        is a list of header strings to print and the second list is a list of values to print.
        The TMTC core will take care of printing both lists and logging them.

        :param object_id: Byte representation of the object ID
        :param action_id:
        :param custom_data:
        :return:
        """
        TestHookObj.service_8_handler_called = True
        return [], []
