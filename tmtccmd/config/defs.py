import enum
from typing import Tuple, Dict, Union

# Com Interface Types
ComIfValueT = Tuple[str, any]
ComIfDictT = Dict[str, ComIfValueT]


def default_json_path() -> str:
    return "tmtc_conf.json"


class CoreComInterfaces(str, enum.Enum):
    value: str

    DUMMY = "dummy"
    UDP = "udp"
    TCP = "tcp"
    SERIAL_FIXED_FRAME = "serial_fixed"
    SERIAL_COBS = "serial_cobs"
    SERIAL_DLE = "serial_dle"
    SERIAL_QEMU = "serial_qemu"
    UNSPECIFIED = "unspec"


CORE_COM_IF_DICT = {
    CoreComInterfaces.DUMMY: ("Dummy Interface", None),
    CoreComInterfaces.SERIAL_DLE: ("Serial Interace with DLE encoding", None),
    CoreComInterfaces.UDP: ("TCP/IP with UDP datagrams", None),
    CoreComInterfaces.TCP: ("TCP/IP with TCP", None),
    CoreComInterfaces.SERIAL_FIXED_FRAME: (
        "Serial Interface with fixed size frames",
        None,
    ),
    CoreComInterfaces.SERIAL_QEMU: ("Serial Interface using QEMU", None),
    CoreComInterfaces.UNSPECIFIED: ("Unspecified", None),
}


# Mode options, set by args parser
class CoreModeList(enum.IntEnum):
    """These are the core modes which will be translated to different TC and TM modes
    for the CCSDS backend

    1. ONE_QUEUE_MODE: This mode is optimized to handle one queue. It will configure the backend
       to request program termination upon finishing the queue handling. This is also the
       appropriate solution for single commands where the queue only consists of one telecommand.
    2. LISTENER_MODE: Only listen to TM
    3. MULTI_INTERACTIVE_QUEUE_MODE:
    """

    #
    ONE_QUEUE_MODE = 0
    LISTENER_MODE = 1
    # This mode is optimized for the handling of multiple queues. It will configure the backend
    # to request additional queues or a mode change from the user instead of requesting program
    # termination
    MULTI_INTERACTIVE_QUEUE_MODE = 3
    # The program will not do anything in this mode. This includes polling TM and sending any TCs
    IDLE = 5


class CoreModeConverter:
    @staticmethod
    def get_str(mode: Union[CoreModeList, int]) -> str:
        if mode == CoreModeList.LISTENER_MODE:
            return "listener"
        elif mode == CoreModeList.ONE_QUEUE_MODE:
            return "one-q"
        elif mode == CoreModeList.MULTI_INTERACTIVE_QUEUE_MODE:
            return "multi-q"
        elif mode == CoreModeList.IDLE:
            return "idle"


class CoreServiceList(str, enum.Enum):
    value: str
    SERVICE_2 = "2"
    SERVICE_3 = "3"
    SERVICE_5 = "5"
    SERVICE_8 = "8"
    SERVICE_9 = "9"
    SERVICE_11 = "11"
    SERVICE_17 = "17"
    SERVICE_17_ALT = "test"
    SERVICE_20 = "20"
    SERVICE_23 = "23"
    SERVICE_200 = "200"


DEFAULT_APID = 0xEF
DEBUG_MODE = False
