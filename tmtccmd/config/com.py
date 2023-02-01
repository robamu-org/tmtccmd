import logging
import sys
from typing import Optional, Tuple, cast, Sequence

from spacepackets.ccsds import PacketId
from tmtccmd.config.defs import CoreComInterfaces
from tmtccmd.config.globals import CoreGlobalIds
from tmtccmd.core.globals_manager import get_global, update_global
from tmtccmd.com import ComInterface
from tmtccmd.com.serial_base import (
    SerialConfigIds,
    SerialCommunicationType,
    SerialCfg,
)

from tmtccmd.com.serial_dle import SerialDleComIF
from tmtccmd.com.serial_fixed_frame import SerialFixedFrameComIF
from tmtccmd.com.serial_cobs import SerialCobsComIF

from tmtccmd.com.ser_utils import determine_com_port, determine_baud_rate
from tmtccmd.com.tcpip_utils import TcpIpType, EthAddr
from tmtccmd.com.udp import UdpComIF
from tmtccmd.com.tcp import TcpSpacePacketsComIF

_LOGGER = logging.getLogger(__name__)


class ComCfgBase:
    def __init__(
        self,
        com_if_key: str,
        json_cfg_path: str,
    ):
        self.com_if_key = com_if_key
        self.json_cfg_path = json_cfg_path


class TcpipCfg(ComCfgBase):
    def __init__(
        self,
        if_type: TcpIpType,
        com_if_key: str,
        json_cfg_path: str,
        send_addr: EthAddr,
        space_packet_ids: Optional[Sequence[PacketId]] = None,
        recv_addr: Optional[EthAddr] = None,
    ):
        super().__init__(com_if_key, json_cfg_path)
        self.space_packet_ids = space_packet_ids
        self.if_type = if_type
        self.send_addr = send_addr
        self.recv_addr = recv_addr


class SerialCfgWrapper(ComCfgBase):
    def __init__(self, com_if_key: str, json_cfg_path: str, serial_cfg: SerialCfg):
        super().__init__(com_if_key=com_if_key, json_cfg_path=json_cfg_path)
        self.serial_cfg = serial_cfg


def create_com_interface_cfg_default(
    com_if_key: str, json_cfg_path: str, space_packet_ids: Optional[Tuple[int]]
) -> Optional[ComCfgBase]:
    if com_if_key == CoreComInterfaces.DUMMY.value:
        return ComCfgBase(com_if_key=com_if_key, json_cfg_path=json_cfg_path)
    elif com_if_key == CoreComInterfaces.UDP.value:
        return default_tcpip_cfg_setup(
            com_if_key=com_if_key,
            json_cfg_path=json_cfg_path,
            tcpip_type=TcpIpType.UDP,
            space_packet_ids=space_packet_ids,
        )
    elif com_if_key == CoreComInterfaces.TCP.value:
        return default_tcpip_cfg_setup(
            com_if_key=com_if_key,
            json_cfg_path=json_cfg_path,
            tcpip_type=TcpIpType.TCP,
            space_packet_ids=space_packet_ids,
        )
    elif com_if_key in [
        CoreComInterfaces.SERIAL_DLE.value,
        CoreComInterfaces.SERIAL_FIXED_FRAME.value,
        CoreComInterfaces.SERIAL_COBS.value,
    ]:
        # For a serial communication interface, there are some configuration values like
        # baud rate and serial port which need to be set once but are expected to stay
        # the same for a given machine. Therefore, we use a JSON file to store and extract
        # those values
        cfg = SerialCfg(
            baud_rate=0, com_if_id=com_if_key, serial_timeout=0, serial_port=""
        )
        default_serial_cfg_baud_and_port_setup(json_cfg_path, cfg)
        return SerialCfgWrapper(
            com_if_key=com_if_key, json_cfg_path=json_cfg_path, serial_cfg=cfg
        )
    else:
        return None


def create_com_interface_default(cfg: ComCfgBase) -> Optional[ComInterface]:
    """Return the desired communication interface object

    :param cfg: Generic configuration
    :return:
    """
    if cfg is None:
        raise ValueError("Passed ComIF configuration is empty")
    if cfg.com_if_key == "":
        _LOGGER.warning("COM Interface key string is empty. Using dummy COM interface")
    try:
        return __create_com_if(cfg)
    except ConnectionRefusedError:
        _LOGGER.exception("TCP/IP connection refused")
        if cfg.com_if_key == CoreComInterfaces.UDP.value:
            _LOGGER.warning("Make sure that a UDP server is running")
        if cfg.com_if_key == CoreComInterfaces.TCP.value:
            _LOGGER.warning("Make sure that a TCP server is running")
        sys.exit(1)
    except (IOError, OSError):
        _LOGGER.exception("Error setting up communication interface")
        sys.exit(1)


def __create_com_if(cfg: ComCfgBase) -> Optional[ComInterface]:
    from tmtccmd.com.dummy import DummyComIF
    from tmtccmd.com.qemu import QEMUComIF

    if (
        cfg.com_if_key == CoreComInterfaces.UDP.value
        or cfg.com_if_key == CoreComInterfaces.TCP.value
    ):
        communication_interface = create_default_tcpip_interface(cast(TcpipCfg, cfg))
    elif cfg.com_if_key in [
        CoreComInterfaces.SERIAL_DLE.value,
        CoreComInterfaces.SERIAL_FIXED_FRAME.value,
        CoreComInterfaces.SERIAL_COBS.value,
    ]:
        serial_cfg_wrapper = cast(SerialCfgWrapper, cfg)
        communication_interface = create_default_serial_interface(
            com_if_key=cfg.com_if_key,
            json_cfg_path=cfg.json_cfg_path,
            serial_cfg=serial_cfg_wrapper.serial_cfg,
        )
    elif cfg.com_if_key == CoreComInterfaces.SERIAL_QEMU.value:
        # TODO: Move to new model where config is passed externally
        serial_cfg = cast(SerialCfg, cfg)
        communication_interface = QEMUComIF(
            com_if_id=cfg.com_if_key,
            serial_timeout=serial_cfg.serial_timeout,
            ser_com_type=SerialCommunicationType.DLE_ENCODING,
        )
    else:
        communication_interface = DummyComIF()
    if communication_interface is None:
        _LOGGER.warning("Invalid communication interface, is None")
        return communication_interface
    communication_interface.initialize()
    return communication_interface


def default_tcpip_cfg_setup(
    com_if_key: str,
    tcpip_type: TcpIpType,
    json_cfg_path: str,
    space_packet_ids: Optional[Sequence[PacketId]],
) -> TcpipCfg:
    """Default setup for TCP/IP communication interfaces. This intantiates all required data in the
    globals manager so a TCP/IP communication interface can be built with
    :func:`create_default_tcpip_interface`

    :param com_if_key:
    :param tcpip_type:
    :param json_cfg_path:
    :param space_packet_ids:       Required if the TCP com interface needs to parse space packets
    :return:
    """
    from tmtccmd.com.tcpip_utils import (
        determine_udp_send_address,
        determine_tcp_send_address,
    )

    # TODO: Is this necessary? Where is it used?
    update_global(CoreGlobalIds.USE_ETHERNET, True)
    if tcpip_type == TcpIpType.UDP:
        send_addr = determine_udp_send_address(json_cfg_path=json_cfg_path)
    elif tcpip_type == TcpIpType.TCP:
        send_addr = determine_tcp_send_address(json_cfg_path=json_cfg_path)
    else:
        send_addr = ()
    cfg = TcpipCfg(
        com_if_key=com_if_key,
        if_type=tcpip_type,
        json_cfg_path=json_cfg_path,
        send_addr=send_addr,
        space_packet_ids=space_packet_ids,
    )
    return cfg


def default_serial_cfg_baud_and_port_setup(json_cfg_path: str, cfg: SerialCfg):
    """Default setup for serial interfaces.

    :param json_cfg_path:
    :param cfg: The baud and serial port parameter will be set in this dataclass
    :return:
    """
    baud_rate = determine_baud_rate(json_cfg_path=json_cfg_path)
    serial_port = determine_com_port(json_cfg_path=json_cfg_path)
    cfg.serial_port = serial_port
    cfg.baud_rate = baud_rate
    """
    set_up_serial_cfg(
        json_cfg_path=json_cfg_path,
        com_if_key=com_if_key,
        baud_rate=baud_rate,
        com_port=serial_port,
    )
    """


def create_default_tcpip_interface(tcpip_cfg: TcpipCfg) -> Optional[ComInterface]:
    """Create a default serial interface. Requires a certain set of global variables set up. See
    :py:func:`default_tcpip_cfg_setup` for more details.

    :param tcpip_cfg: Configuration parameters
    :return:
    """
    communication_interface = None
    if tcpip_cfg.com_if_key == CoreComInterfaces.UDP.value:
        communication_interface = UdpComIF(
            com_if_id=tcpip_cfg.com_if_key,
            send_address=tcpip_cfg.send_addr,
            recv_addr=tcpip_cfg.recv_addr,
        )
    elif tcpip_cfg.com_if_key == CoreComInterfaces.TCP.value:
        communication_interface = TcpSpacePacketsComIF(
            com_if_id=tcpip_cfg.com_if_key,
            space_packet_ids=tcpip_cfg.space_packet_ids,
            tm_polling_freqency=0.5,
            target_address=tcpip_cfg.send_addr,
        )
    return communication_interface


# TODO: Pass configuration explicitely instead of using globals..
def create_default_serial_interface(
    com_if_key: str, json_cfg_path: str, serial_cfg: SerialCfg
) -> Optional[ComInterface]:

    """Create a default serial interface. Requires a certain set of global variables set up. See
    :func:`set_up_serial_cfg` for more details.

    :param com_if_key:
    :param json_cfg_path:
    :param serial_cfg: Generic serial configuration parameters
    :return:
    """
    try:
        if com_if_key == CoreComInterfaces.SERIAL_DLE.value:
            # Ignore the DLE config for now, it is not that important anyway
            communication_interface = SerialDleComIF(ser_cfg=serial_cfg, dle_cfg=None)
        elif com_if_key == CoreComInterfaces.SERIAL_FIXED_FRAME.value:
            communication_interface = SerialFixedFrameComIF(ser_cfg=serial_cfg)
        elif com_if_key == CoreComInterfaces.SERIAL_COBS.value:
            communication_interface = SerialCobsComIF(ser_cfg=serial_cfg)
        else:
            # TODO: Maybe print valid keys?
            _LOGGER.warning(f"Invalid COM IF key {com_if_key} for a serial interface")
            return None
    except KeyError as e:
        _LOGGER.warning("Serial configuration global not configured properly")
        raise e
    return communication_interface


# TODO: Get rid of thisq
def set_up_serial_cfg(
    json_cfg_path: str,
    com_if_key: str,
    baud_rate: int,
    com_port: str = "",
    tm_timeout: float = 0.01,
    ser_com_type: SerialCommunicationType = SerialCommunicationType.DLE_ENCODING,
    ser_frame_size: int = 256,
    dle_queue_len: int = 25,
    dle_frame_size: int = 1024,
):
    """Default configuration to set up serial communication. The serial port and the baud rate
    will be determined from a JSON configuration file and prompted from the user. Sets up all
    global variables so that a serial communication interface can be built with
    py:func:`create_default_serial_interface`.

    :param json_cfg_path:
    :param com_if_key:
    :param com_port:
    :param baud_rate:
    :param tm_timeout:
    :param ser_com_type:
    :param ser_frame_size:
    :param dle_queue_len:
    :param dle_frame_size:
    :return:
    """
    update_global(CoreGlobalIds.USE_SERIAL, True)
    if (
        com_if_key == CoreComInterfaces.SERIAL_DLE.value
        or com_if_key == CoreComInterfaces.SERIAL_FIXED_FRAME.value
    ) and com_port == "":
        _LOGGER.warning("Invalid serial port specified!")
        com_port = determine_com_port(json_cfg_path=json_cfg_path)
    serial_cfg_dict = get_global(CoreGlobalIds.SERIAL_CONFIG)
    serial_cfg_dict.update({SerialConfigIds.SERIAL_PORT: com_port})
    serial_cfg_dict.update({SerialConfigIds.SERIAL_BAUD_RATE: baud_rate})
    serial_cfg_dict.update({SerialConfigIds.SERIAL_TIMEOUT: tm_timeout})
    serial_cfg_dict.update({SerialConfigIds.SERIAL_COMM_TYPE: ser_com_type})
    serial_cfg_dict.update({SerialConfigIds.SERIAL_FRAME_SIZE: ser_frame_size})
    serial_cfg_dict.update({SerialConfigIds.SERIAL_DLE_QUEUE_LEN: dle_queue_len})
    serial_cfg_dict.update({SerialConfigIds.SERIAL_DLE_MAX_FRAME_SIZE: dle_frame_size})
    update_global(CoreGlobalIds.SERIAL_CONFIG, serial_cfg_dict)
