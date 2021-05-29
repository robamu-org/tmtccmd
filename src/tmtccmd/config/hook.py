import sys
import argparse
from abc import abstractmethod
from typing import Union, Dict, Tuple

from tmtccmd.config.definitions import DEFAULT_APID, ServiceOpCodeDictT
from tmtccmd.utility.logger import get_logger
from tmtccmd.core.backend import TmTcHandler
from tmtccmd.utility.tmtc_printer import TmTcPrinter
from tmtccmd.ecss.tm import PusTelemetry
from tmtccmd.pus_tc.definitions import TcQueueT
from tmtccmd.com_if.com_interface_base import CommunicationInterface
from tmtccmd.pus_tm.service_3_base import Service3Base

LOGGER = get_logger()


class TmTcHookBase:
    def __init__(self):
        pass

    @abstractmethod
    def get_version(self) -> str:
        from tmtccmd import VERSION_NAME, __version__
        return f"{VERSION_NAME} {__version__}"

    @abstractmethod
    def get_object_ids(self) -> Dict[bytes, list]:
        """
        The user can specify an object ID dictionary here mapping object ID bytearrays to a list (e.g. containing
        the string representation)
        """
        pass

    @abstractmethod
    def add_globals_pre_args_parsing(self, gui: bool = False):
        """
        Add all global variables prior to parsing the CLI arguments.
        :param gui: Set to true if the GUI mode is used
        :return:
        """
        from tmtccmd.config.globals import set_default_globals_pre_args_parsing
        set_default_globals_pre_args_parsing(gui=gui, apid=DEFAULT_APID)

    @abstractmethod
    def get_json_config_file_path(self) -> str:
        """
        The user can specify a path and filename for the JSON configuration file by overriding this function.
        :return:
        """
        return "tmtc_config.json"

    @abstractmethod
    def add_globals_post_args_parsing(self, args: argparse.Namespace):
        """
        Add global variables prior after parsing the CLI arguments.
        :param args:  Specify whether a GUI is used
        """
        from tmtccmd.config.globals import set_default_globals_post_args_parsing
        set_default_globals_post_args_parsing(args=args, json_cfg_path=self.get_json_config_file_path())

    @abstractmethod
    def assign_communication_interface(
            self, com_if_key: str, tmtc_printer: TmTcPrinter
    ) -> Union[CommunicationInterface, None]:
        """
        Assign the communication interface used by the TMTC commander to send and receive TMTC with.
        :param com_if_key:      String key of the communication interface to be created.
        :param tmtc_printer:    Printer utility instance.
        """
        from tmtccmd.config.com_if import create_communication_interface_default
        return create_communication_interface_default(
            com_if_key=com_if_key, tmtc_printer=tmtc_printer, json_cfg_path=self.get_json_config_file_path()
        )

    @abstractmethod
    def get_service_op_code_dictionary(self) -> ServiceOpCodeDictT:
        from tmtccmd.config.globals import get_default_service_op_code_dict
        return get_default_service_op_code_dict()

    @abstractmethod
    def perform_mode_operation(self, tmtc_backend: TmTcHandler, mode: int):
        pass

    @abstractmethod
    def pack_service_queue(self, service: Union[int, str], op_code: str, service_queue: TcQueueT):
        pass

    @abstractmethod
    def tm_user_factory_hook(self, raw_tm_packet: bytearray) -> Union[None, PusTelemetry]:
        pass

    @staticmethod
    def custom_args_parsing() -> Union[None, argparse.Namespace]:
        """
        The user can implement args parsing here to override the default argument parsing for
        the CLI mode
        :return
        """
        return None

    @staticmethod
    def handle_service_8_telemetry(
            object_id: bytes, action_id: int, custom_data: bytearray
    ) -> Tuple[list, list]:
        """
        This function is called by the TMTC core if a Service 8 data reply (subservice 130)
        is received. The user can return a tuple of two lists, where the first list
        is a list of header strings to print and the second list is a list of values to print.
        The TMTC core will take care of printing both lists and logging them.

        :param object_id:   Object ID bytearray
        :param action_id:
        :param custom_data:
        :return:
        """
        LOGGER.info(
            "TmTcHookBase: No service 8 handling implemented yet in handle_service_8_telemetry "
            "hook function"
        )
        return [], []

    @staticmethod
    def handle_service_3_housekeeping(
        object_id: bytes, set_id: int, hk_data: bytearray, service3_packet: Service3Base
    ) -> Tuple[list, list, bytearray, int]:
        """
        This function is called when a Service 3 Housekeeping packet is received.
        :param object_id: Integer representation of the found object ID.
        See the:func:`tmtccmd.core.hook_base.set_object_ids` function for more information
        :param set_id: Unique set ID of the HK reply
        :param hk_data: HK data. For custom HK handling, whole HK data will be passed here. Otherwise, a 8 byte SID
        consisting of the 4 byte object ID and 4 byte set ID will be assumed and the remaining packet after the first
        4 bytes will be passed here.
        :param service3_packet: Service 3 packet object
        :return: Expects a tuple, consisting of two lists, a bytearray and an integer
        The first list contains the header columns, the second list the list with
        the corresponding values. The bytearray is the validity buffer, which is usually appended
        at the end of the housekeeping packet. The last value is the number of parameters.
        """
        LOGGER.info(
            "TmTcHookBase: No service 3 housekeeping data handling implemented yet in "
            "handle_service_3_housekeeping hook function"
        )
        return [], [], bytearray(), 0

    @staticmethod
    def handle_service_5_event(
        object_id: bytes, event_id: int, param_1: int, param_2: int
    ) -> str:
        """
        This function is called when a Service 5 Event Packet is received. The user can specify a custom
        string here which will be printed to display additional information related to an event.
        :param object_id:       Integer representation of the found object ID. See
                                the :func:`tmtccmd.core.hook_base.set_object_ids` function for more information
        :param event_id:        Two-byte event ID
        :param param_1:         Four-byte Parameter 1
        :param param_2:         Four-byte Parameter 2
        :return:    Custom information string which will be printed with the event
        """
        return ""


def get_global_hook_obj() -> Union[None, TmTcHookBase]:
    try:
        from tmtccmd.core.globals_manager import get_global
        from tmtccmd.config.definitions import CoreGlobalIds

        from typing import cast
        hook_obj_raw = get_global(CoreGlobalIds.TMTC_HOOK)
        if hook_obj_raw is None:
            LOGGER.error("Hook object is invalid!")
            sys.exit(0)
        return cast(TmTcHookBase, hook_obj_raw)
    except ImportError:
        LOGGER.exception("Issues importing modules to get global hook handle!")
        return None
    except AttributeError:
        LOGGER.exception("Attribute error when trying to get global hook handle!")
        return None
