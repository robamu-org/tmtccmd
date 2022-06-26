"""Definitions for the TMTC commander core
"""
import argparse
import enum
from abc import abstractmethod
from typing import Tuple, Dict, Optional

from tmtccmd.logging import get_console_logger
from tmtccmd.com_if import ComInterface
from tmtccmd.config.args import (
    SetupParams,
    create_default_args_parser,
    add_default_tmtccmd_args,
    parse_default_tmtccmd_input_arguments,
)
from tmtccmd.config.prompt import prompt_op_code, prompt_service
from tmtccmd.config.tmtc import TmTcDefWrapper
from tmtccmd.core import ModeWrapper, TmMode, TcMode, BackendBase
from tmtccmd.utility.obj_id import ObjectIdDictT
from tmtccmd.utility.retval import RetvalDictT


LOGGER = get_console_logger()

# Com Interface Types
ComIfValueT = Tuple[str, any]
ComIfDictT = Dict[str, ComIfValueT]


def default_json_path() -> str:
    return "tmtc_conf.json"


class CoreComInterfaces(enum.Enum):
    DUMMY = "dummy"
    SERIAL_DLE = "ser_dle"
    UDP = "udp"
    TCP = "tcp"
    SERIAL_FIXED_FRAME = "ser_fixed"
    SERIAL_QEMU = "ser_qemu"
    UNSPECIFIED = "unspec"


CORE_COM_IF_DICT = {
    CoreComInterfaces.DUMMY.value: "Dummy Interface",
    CoreComInterfaces.SERIAL_DLE.value: "Serial Interace with DLE encoding",
    CoreComInterfaces.UDP.value: "TCP/IP with UDP datagrams",
    CoreComInterfaces.TCP.value: "TCP/IP with TCP",
    CoreComInterfaces.SERIAL_FIXED_FRAME.value: "Serial Interface with fixed size frames",
    CoreComInterfaces.SERIAL_QEMU.value: "Serial Interface using QEMU",
    CoreComInterfaces.UNSPECIFIED.value: "Unspecified",
}


# Mode options, set by args parser
class CoreModeList(enum.IntEnum):
    # This mode is optimized to handle one queue. It will configure the backend to request
    # program termination upon finishing the queue handling. This is also the appropriate solution
    # for single commands where the queue only consists of one telecommand.
    ONE_QUEUE_MODE = 0
    LISTENER_MODE = 1
    # Interactive GUI mode which allows sending and handling procedures interactively
    GUI_MODE = 2
    # This mode is optimized for the handling of multiple queues. It will configure the backend
    # to request additional queues or a mode change from the user instead of requesting program
    # termination
    MULTI_INTERACTIVE_QUEUE_MODE = 3
    # The program will not do anything in this mode. This includes polling TM and sending any TCs
    IDLE = 5


CoreModeStrings = {
    CoreModeList.ONE_QUEUE_MODE: "one-q",
    CoreModeList.MULTI_INTERACTIVE_QUEUE_MODE: "multi-q",
    CoreModeList.LISTENER_MODE: "listener",
    CoreModeList.IDLE: "idle",
    CoreModeList.GUI_MODE: "gui",
}


def backend_mode_conversion(mode: CoreModeList, mode_wrapper: ModeWrapper):
    if mode == CoreModeStrings[CoreModeList.LISTENER_MODE]:
        mode_wrapper.tm_mode = TmMode.LISTENER
        mode_wrapper.tc_mode = TcMode.IDLE
    elif mode == CoreModeStrings[CoreModeList.ONE_QUEUE_MODE]:
        mode_wrapper.tm_mode = TmMode.LISTENER
        mode_wrapper.tc_mode = TcMode.ONE_QUEUE
    elif mode == CoreModeStrings[CoreModeList.MULTI_INTERACTIVE_QUEUE_MODE]:
        mode_wrapper.tc_mode = TcMode.MULTI_QUEUE
        mode_wrapper.tm_mode = TmMode.LISTENER
    elif mode == CoreModeStrings[CoreModeList.GUI_MODE]:
        mode_wrapper.tc_mode = TcMode.MULTI_QUEUE
        mode_wrapper.tm_mode = TmMode.IDLE


class CoreServiceList(enum.Enum):
    SERVICE_2 = "2"
    SERVICE_3 = "3"
    SERVICE_5 = "5"
    SERVICE_8 = "8"
    SERVICE_9 = "9"
    SERVICE_11 = "11"
    SERVICE_17 = "17"
    SERVICE_20 = "20"
    SERVICE_23 = "23"
    SERVICE_200 = "200"


DEFAULT_APID = 0xEF
DEBUG_MODE = False


class TmTcCfgHookBase:
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
    def assign_communication_interface(self, com_if_key: str) -> Optional[ComInterface]:
        """Assign the communication interface used by the TMTC commander to send and receive
        TMTC with.

        :param com_if_key:      String key of the communication interface to be created.
        """
        from tmtccmd.config.com_if import create_communication_interface_default

        return create_communication_interface_default(
            com_if_key=com_if_key, json_cfg_path=self.json_cfg_path
        )

    def get_com_if_dict(self) -> ComIfDictT:
        return CORE_COM_IF_DICT

    @abstractmethod
    def get_tmtc_definitions(self) -> TmTcDefWrapper:
        """This is a dicitonary mapping services represented by strings to an operation code
        dictionary.

        :return:
        """
        from tmtccmd.config.globals import get_default_tmtc_defs

        return get_default_tmtc_defs()

    @abstractmethod
    def perform_mode_operation(self, tmtc_backend: BackendBase, mode: int):
        """Perform custom mode operations
        :param tmtc_backend:
        :param mode:
        :return:
        """
        pass

    def get_retval_dict(self) -> RetvalDictT:
        from tmtccmd import get_console_logger

        logger = get_console_logger()
        logger.info("No return value dictionary specified")
        return dict()


def get_global_hook_obj() -> Optional[TmTcCfgHookBase]:
    """This function can be used to get the handle to the global hook object.
    :return:
    """
    from tmtccmd import get_console_logger

    logger = get_console_logger()
    try:
        from tmtccmd.core.globals_manager import get_global
        from tmtccmd.config.definitions import CoreGlobalIds

        from typing import cast

        hook_obj_raw = get_global(CoreGlobalIds.TMTC_HOOK)
        if hook_obj_raw is None:
            logger.error("Hook object is invalid!")
            return None
        return cast(TmTcCfgHookBase, hook_obj_raw)
    except ImportError:
        logger.exception("Issues importing modules to get global hook handle!")
        return None
    except AttributeError:
        logger.exception("Attribute error when trying to get global hook handle!")
        return None


def args_to_params(
    args: argparse.Namespace, hook_obj: TmTcCfgHookBase, use_prompts: bool
) -> SetupParams:
    """If some arguments are unspecified, they are set here with (variable) default values.

    :param args: Arguments from calling parse method
    :param hook_obj:
    :param use_prompts: Specify whether terminal prompts are allowed to retrieve unspecified
        arguments. For something like a GUI, it might make sense to disable this
    :return: None
    """
    from tmtccmd.com_if.utils import determine_com_if

    group = SetupParams()
    if args.com_if is None or args.com_if == CoreComInterfaces.UNSPECIFIED.value:
        if use_prompts:
            group.com_if = determine_com_if(
                hook_obj.get_com_if_dict(), hook_obj.json_cfg_path
            )
    else:
        # TODO: Check whether COM IF is valid?
        group.com_if = args.com_if
    if args.mode is None:
        group.mode = CoreModeStrings[CoreModeList.ONE_QUEUE_MODE]
    else:
        group.mode = args.mode
    tmtc_defs = hook_obj.get_tmtc_definitions()
    if tmtc_defs is None:
        LOGGER.warning("Invalid Service to Op-Code dictionary detected")
        if args.service is None:
            group.service = "0"
        if args.op_code is None:
            group.op_code = "0"
    else:
        if args.service is None:
            if args.mode == CoreModeStrings[CoreModeList.ONE_QUEUE_MODE]:
                if use_prompts:
                    LOGGER.info(
                        "No service argument (-s) specified, prompting from user.."
                    )
                    # Try to get the service list from the hook base and prompt service from user
                    group.service = prompt_service(tmtc_defs)
        else:
            group.service = args.service
        if args.op_code is None:
            current_service = group.service
            if use_prompts:
                group.op_code = prompt_op_code(tmtc_defs, current_service)
        else:
            group.op_code = args.op_code
    if args.delay is None:
        if group.mode == CoreModeStrings[CoreModeList.ONE_QUEUE_MODE]:
            group.delay = 3.0
        else:
            group.delay = 0.0
    else:
        group.delay = args.delay
    if args.listener is None:
        args.listener = False
    else:
        group.listener = args.listener
    return group


class ArgParserWrapper:
    def __init__(
        self,
        parser: Optional[argparse.ArgumentParser] = None,
        descript_txt: Optional[str] = None,
    ):
        if parser is None:
            self.args_parser = create_default_args_parser(descript_txt)
            add_default_tmtccmd_args(self.args_parser)
        else:
            self.args_parser = parser
        self.print_known_args = False
        self.print_unknown_args = False
        self.unknown_args = [""]
        self._params: SetupParams = SetupParams()
        self.args_raw = None

    def add_default_tmtccmd_args(self):
        add_default_tmtccmd_args(self.args_parser)

    def parse(self, hook_obj: TmTcCfgHookBase, use_prompts: bool):
        self.args_raw, self.unknown_args = parse_default_tmtccmd_input_arguments(
            self.args_parser,
            print_known_args=self.print_known_args,
            print_unknown_args=self.print_unknown_args,
        )
        self._params = args_to_params(self.args_raw, hook_obj, use_prompts)

    @property
    def params(self):
        return self._params

    @property
    def delay(self):
        return self.params.tc_properties.delay

    @property
    def service(self):
        return self.params.def_proc_args.service

    @property
    def op_code(self):
        return self.params.def_proc_args.op_code

    @property
    def mode(self):
        return self.params.backend_params.mode

    @property
    def com_if(self):
        return self.params.backend_params.com_if


class SetupWrapper:
    """This class encapsulates various important setup parameters required by tmtccmd components"""

    def __init__(
        self,
        hook_obj: TmTcCfgHookBase,
        use_gui: bool,
        apid: int,
        setup_params: SetupParams,
        json_cfg_path: Optional[str] = None,
        reduced_printout: bool = False,
        use_ansi_colors: bool = True,
    ):
        """
        :param hook_obj: User hook object. Needs to be implemented by the user
        :param setup_params: Optional helper wrapper which contains CLI arguments.
        :param use_gui: Specify whether a GUI is used.
        :param reduced_printout:
        :param use_ansi_colors:
        """
        self.hook_obj = hook_obj
        self.use_gui = use_gui
        self.apid = apid
        self.json_cfg_path = json_cfg_path
        self.reduced_printout = reduced_printout
        self.ansi_colors = use_ansi_colors
        self.args_wrapper = setup_params
        self.json_cfg_path = json_cfg_path
        if json_cfg_path is None:
            self.json_cfg_path = default_json_path()
