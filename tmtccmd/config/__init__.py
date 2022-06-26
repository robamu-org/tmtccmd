"""Definitions for the TMTC commander core
"""
import enum
from abc import abstractmethod
from typing import Tuple, Dict, Optional


from tmtccmd.com_if import ComInterface
from tmtccmd.config.tmtc_defs import TmTcDefWrapper
from tmtccmd.core import ModeWrapper, TmMode, TcMode, BackendBase
from tmtccmd.utility.obj_id import ObjectIdDictT
from tmtccmd.utility.retval import RetvalDictT


def default_json_path() -> str:
    return "tmtc_conf.json"


# Com Interface Types
ComIfValueT = Tuple[str, any]
ComIfDictT = Dict[str, ComIfValueT]

EthernetAddressT = Tuple[str, int]


class CoreComInterfaces(enum.Enum):
    DUMMY = "dummy"
    SERIAL_DLE = "ser_dle"
    TCPIP_UDP = "udp"
    TCPIP_TCP = "tcp"
    SERIAL_FIXED_FRAME = "ser_fixed"
    SERIAL_QEMU = "ser_qemu"
    UNSPECIFIED = "unspec"


CORE_COM_IF_DICT = {
    CoreComInterfaces.DUMMY.value: "Dummy Interface",
    CoreComInterfaces.SERIAL_DLE.value: "Serial Interace with DLE encoding",
    CoreComInterfaces.TCPIP_UDP.value: "TCP/IP with UDP datagrams",
    CoreComInterfaces.TCPIP_TCP.value: "TCP/IP with TCP",
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
