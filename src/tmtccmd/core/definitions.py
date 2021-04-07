"""
@brief  Definitions for the TMTC commander core
"""

import enum
from typing import Tuple

ethernet_address_t = Tuple[str, int]


class CoreComInterfaces(enum.IntEnum):
    DUMMY = 0
    SERIAL = 1
    TCPIP_UDP = 2
    QEMU_SERIAL = 5


class QueueCommands(enum.Enum):
    PRINT = enum.auto()
    RAW_PRINT = enum.auto()
    WAIT = enum.auto()
    EXPORT_LOG = enum.auto()
    SET_TIMEOUT = enum.auto()


class CoreObjectIds(enum.IntEnum):
    INVALID = 999


# Mode options, set by args parser
class CoreModeList(enum.IntEnum):
    SINGLE_CMD_MODE = 0
    SEQUENTIAL_CMD_MODE = 1
    LISTENER_MODE = 2
    GUI_MODE = 3
    SOFTWARE_TEST_MODE = 4
    IDLE = 5
    PROMPT_MODE = 6


class CoreServiceList(enum.IntEnum):
    SERVICE_2 = 2
    SERVICE_3 = 3
    SERVICE_5 = 5
    SERVICE_8 = 8
    SERVICE_9 = 9
    SERVICE_11 = 11
    SERVICE_17 = 17
    SERVICE_20 = 20
    SERVICE_23 = 23
    SERVICE_200 = 200


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

    # PUS specific
    CUSTOM_HK_REPORT_FORMAT = 164


DEFAULT_APID = 0xef
DEBUG_MODE = False

