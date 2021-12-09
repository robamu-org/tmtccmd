"""Definitions for the TMTC commander core
"""
import enum
from typing import Tuple, Dict, Optional, List, Union


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
    CFDP_HANDLER_HANDLE = 133
    TMTC_BACKEND = 134
    PRETTY_PRINTER = 135

    # Core Parameters
    JSON_CFG_PATH = 139
    COM_IF_DICT = 140
    MODE = 141
    COM_IF = 142
    SEQ_CMD_CFG = 144

    # CFDP
    CFDP_CFG = 150

    # Miscellaneous
    PRINT_TO_FILE = 155

    # Config dictionaries
    USE_SERIAL = 160
    SERIAL_CONFIG = 161
    USE_ETHERNET = 162
    ETHERNET_CONFIG = 163


class OpCodeDictKeys(enum.IntEnum):
    TIMEOUT = 0


# Service Op Code Dictionary Types
ServiceNameT = str
ServiceInfoT = str
OpCodeNameT = Union[str, List[str]]
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
    CoreComInterfaces.UNSPECIFIED.value: "Unspecified",
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
    CFDP_MODE = 2
    GUI_MODE = 3
    IDLE = 5
    PROMPT_MODE = 6


CoreModeStrings = {
    CoreModeList.SEQUENTIAL_CMD_MODE: "seqcmd",
    CoreModeList.LISTENER_MODE: "listener",
    CoreModeList.CFDP_MODE: "cfdp",
    CoreModeList.GUI_MODE: "gui",
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


class SeqTransferCfg:
    service = CoreServiceList.SERVICE_17
    op_code = "0"
    tm_timeout = 2.0
    tc_send_timeout_factor = 2.5
    resend_tc = False
    print_hk = False
    print_tm = True
    print_raw_tm = True
    display_mode = "long"
    service_op_code_dict = dict()
    listener_after_op = False


DEFAULT_APID = 0xEF
DEBUG_MODE = False
