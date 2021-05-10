"""
@brief  Definitions for the TMTC commander core
"""
import enum
from typing import Tuple, Dict, Union

ServiceNameT = str
ServiceInfoT = str
OpCodeNameT = str
OpCodeInfoT = str
# Operation code options are optional. If none are supplied, default values are assumed
OpCodeOptionsT = Union[None, Dict[str, any]]
OpCodeEntryT = Dict[OpCodeNameT, Tuple[OpCodeInfoT, OpCodeOptionsT]]
# It is possible to specify a service without any op codes
ServiceDictValueT = Union[None, Tuple[ServiceInfoT, OpCodeEntryT]]
ServiceOpCodeDictT = Dict[ServiceNameT, ServiceDictValueT]
ethernet_address_t = Tuple[str, int]


class CoreComInterfaces(enum.IntEnum):
    DUMMY = 0
    SERIAL_DLE = 1
    TCPIP_UDP = 2
    SERIAL_FIXED_FRAME = 4
    SERIAL_QEMU = 5
    UNSPECIFIED = 0xffff


CoreComInterfacesString = {
    CoreComInterfaces.DUMMY: "dummy",
    CoreComInterfaces.SERIAL_DLE: "ser_dle",
    CoreComInterfaces.TCPIP_UDP: "udp",
    CoreComInterfaces.SERIAL_FIXED_FRAME: "ser_fixed",
    CoreComInterfaces.SERIAL_QEMU: "ser_qemu",
    CoreComInterfaces.UNSPECIFIED: "unspec"
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


class CoreGlobalIds(enum.IntEnum):
    """
    Numbers from 128 to 200 are reserved for core globals
    """
    # Object handles
    TMTC_HOOK = 128
    COM_INTERFACE_HANDLE = 129
    TM_LISTENER_HANDLE = 130
    TMTC_PRINTER_HANDLE = 131
    PRETTY_PRINTER = 132

    # Parameters
    JSON_CFG_PATH = 139
    APID = 140
    MODE = 141
    CURRENT_SERVICE = 142
    SERVICE_DICT = 143
    COM_IF = 144
    OP_CODE = 145
    TM_TIMEOUT = 146
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


DEFAULT_APID = 0xef
DEBUG_MODE = False
SERVICE_OP_CODE_DICT = dict()


def get_default_service_op_code_dict() -> ServiceOpCodeDictT:
    global service_op_code_dict
    if SERVICE_OP_CODE_DICT == dict():
        service_2_tuple = ("PUS Service 2 Raw CMD", None)
        service_3_tuple = ("PUS Service 3 Housekeeping", None)
        op_code_dict_srv_5 = {
            "0": ("Event Test", {OpCodeDictKeys.TIMEOUT: 2.0}),
        }
        service_5_tuple = ("PUS Service 5 Event", op_code_dict_srv_5)
        service_8_tuple = ("PUS Service 8 Functional CMD", None)
        service_9_tuple = ("PUS Service 9 Time", None)
        service_11_tuple = ("PUS Service 11 TC Scheduling", None)
        op_code_dict_srv_17 = {
            "0": ("Ping Test", {OpCodeDictKeys.TIMEOUT: 2.2}),
        }
        service_17_tuple = ("PUS Service 17 Test", op_code_dict_srv_17)
        service_20_tuple = ("PUS Service 20 Parameters", None)
        service_23_tuple = ("PUS Service 23 File MGMT", None)

        service_op_code_dict[CoreServiceList.SERVICE_2.value] = service_2_tuple
        service_op_code_dict[CoreServiceList.SERVICE_3.value] = service_3_tuple
        service_op_code_dict[CoreServiceList.SERVICE_5.value] = service_5_tuple
        service_op_code_dict[CoreServiceList.SERVICE_17.value] = service_17_tuple
        service_op_code_dict[CoreServiceList.SERVICE_20.value] = service_20_tuple
        service_op_code_dict[CoreServiceList.SERVICE_23.value] = service_23_tuple
    return service_op_code_dict