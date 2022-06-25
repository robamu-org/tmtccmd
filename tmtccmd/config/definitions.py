"""Definitions for the TMTC commander core
"""
import enum
from typing import Tuple, Dict

from tmtccmd.core.modes import ModeWrapper, TmMode, TcMode


def default_json_path() -> str:
    return "tmtc_conf.json"


class CoreGlobalIds(enum.IntEnum):
    """
    Numbers from 128 to 200 are reserved for core globals
    """

    # Object handles
    TMTC_HOOK = 128
    COM_INTERFACE_HANDLE = 129
    TM_LISTENER_HANDLE = 130
    TMTC_PRINTER_HANDLE = 131
    TM_HANDLER_HANDLE = 132
    PRETTY_PRINTER = 133

    # Parameters
    JSON_CFG_PATH = 139
    MODE = 141
    CURRENT_SERVICE = 142
    COM_IF = 144
    OP_CODE = 145
    TM_TIMEOUT = 146
    SERVICE_OP_CODE_DICT = 147
    COM_IF_DICT = 148

    # Miscellaneous
    DISPLAY_MODE = 150
    USE_LISTENER_AFTER_OP = 151
    PRINT_HK = 152
    PRINT_TM = 153
    PRINT_RAW_TM = 154
    PRINT_TO_FILE = 155
    RESEND_TC = 156
    TC_SEND_TIMEOUT_FACTOR = 157

    # Config dictionaries
    USE_SERIAL = 160
    SERIAL_CONFIG = 161
    USE_ETHERNET = 162
    ETHERNET_CONFIG = 163
    END = 300


class OpCodeDictKeys(enum.IntEnum):
    TIMEOUT = CoreGlobalIds.TM_TIMEOUT
    ENTER_LISTENER_MODE = CoreGlobalIds.USE_LISTENER_AFTER_OP


# Com Interface Types
ComIFValueT = Tuple[str, any]
ComIFDictT = Dict[str, ComIFValueT]

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
