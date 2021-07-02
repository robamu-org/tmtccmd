"""
@brief  Definitions for the TMTC commander core
"""
import enum
from typing import Tuple, Dict, Optional, List, Deque


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
    APID = 140
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


class OpCodeDictKeys(enum.IntEnum):
    TIMEOUT = CoreGlobalIds.TM_TIMEOUT


# Service Op Code Dictionary Types
ServiceNameT = str
ServiceInfoT = str
OpCodeNameT = str
OpCodeInfoT = str
# Operation code options are optional. If none are supplied, default values are assumed
OpCodeOptionsT = Optional[Dict[OpCodeDictKeys, any]]
OpCodeEntryT = Dict[OpCodeNameT, Tuple[OpCodeInfoT, OpCodeOptionsT]]
# It is possible to specify a service without any op codes
ServiceDictValueT = Optional[Tuple[ServiceInfoT, OpCodeEntryT]]
ServiceOpCodeDictT = Dict[ServiceNameT, ServiceDictValueT]

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


CoreComInterfacesDict = {
    CoreComInterfaces.DUMMY.value: "Dummy Interface",
    CoreComInterfaces.SERIAL_DLE.value: "Serial Interace with DLE encoding",
    CoreComInterfaces.TCPIP_UDP.value: "TCP/IP with UDP datagrams",
    CoreComInterfaces.TCPIP_TCP.value: "TCP/IP with TCP",
    CoreComInterfaces.SERIAL_FIXED_FRAME.value: "Serial Interface with fixed size frames",
    CoreComInterfaces.SERIAL_QEMU.value: "Serial Interface using QEMU",
    CoreComInterfaces.UNSPECIFIED.value: "Unspecified"
}


class QueueCommands(enum.Enum):
    PRINT = enum.auto()
    RAW_PRINT = enum.auto()
    WAIT = enum.auto()
    EXPORT_LOG = enum.auto()
    SET_TIMEOUT = enum.auto()


# Mode options, set by args parser
class CoreModeList(enum.IntEnum):
    SEQUENTIAL_CMD_MODE = 0
    LISTENER_MODE = 1
    GUI_MODE = 2
    IDLE = 5
    PROMPT_MODE = 6


CoreModeStrings = {
    CoreModeList.SEQUENTIAL_CMD_MODE: "seqcmd",
    CoreModeList.LISTENER_MODE: "listener",
    CoreModeList.GUI_MODE: "gui"
}


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


DEFAULT_APID = 0xef
DEBUG_MODE = False
