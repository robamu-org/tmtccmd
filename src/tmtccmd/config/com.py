import logging
import sys
from collections.abc import Sequence
from typing import cast

from com_interface import ComInterface
from com_interface.serial_base import (
    SerialCfg,
)
from com_interface.serial_cobs import SerialCobsComIF
from com_interface.serial_dle import SerialDleComIF
from com_interface.tcp import TcpSpacepacketsClient
from com_interface.udp import UdpClient
from spacepackets.ccsds import PacketId

from tmtccmd.com.ser_utils import determine_baud_rate, determine_com_port
from tmtccmd.com.tcpip_utils import (
    EthAddr,
    TcpIpType,
    determine_tcp_send_address,
    determine_udp_send_address,
)
from tmtccmd.config.defs import CoreComInterfaces

_LOGGER = logging.getLogger(__name__)


class ComConfigCommon:
    def __init__(
        self,
        com_if_key: str,
        cfg_path: str,
    ):
        self.com_if_key = com_if_key
        self.cfg_path = cfg_path

    def __repr__(self):
        return f"ComConfigCommon(com_if_key={self.com_if_key}, cfg_path={self.cfg_path})"

    def __str__(self):
        return self.__repr__()


class TcpipConfig(ComConfigCommon):
    def __init__(
        self,
        if_type: TcpIpType,
        com_if_key: str,
        config_path: str,
        send_addr: EthAddr,
        space_packet_ids: Sequence[PacketId] | None,
        recv_addr: EthAddr | None = None,
    ):
        super().__init__(com_if_key, config_path)
        self.space_packet_ids = space_packet_ids
        self.if_type = if_type
        self.send_addr = send_addr
        self.recv_addr = recv_addr


class SerialConfigCommon(ComConfigCommon):
    def __init__(self, com_if_key: str, config_path: str, serial_cfg: SerialCfg):
        super().__init__(com_if_key=com_if_key, cfg_path=config_path)
        self.serial_cfg = serial_cfg


class DummyConfig(ComConfigCommon):
    pass


def create_com_interface_config_default(
    com_if_key: str, cfg_path: str, space_packet_ids: Sequence[PacketId] | None
) -> TcpipConfig | SerialConfigCommon | DummyConfig | None:
    if com_if_key == CoreComInterfaces.DUMMY.value:
        return DummyConfig(com_if_key=com_if_key, cfg_path=cfg_path)
    elif com_if_key == CoreComInterfaces.UDP.value:
        return default_tcpip_config(
            com_if_key=com_if_key,
            cfg_path=cfg_path,
            tcpip_type=TcpIpType.UDP,
            space_packet_ids=space_packet_ids,
        )
    elif com_if_key == CoreComInterfaces.TCP.value:
        assert space_packet_ids is not None
        return default_tcpip_config(
            com_if_key=com_if_key,
            cfg_path=cfg_path,
            tcpip_type=TcpIpType.TCP,
            space_packet_ids=space_packet_ids,
        )
    elif com_if_key in [
        CoreComInterfaces.SERIAL_DLE.value,
        CoreComInterfaces.SERIAL_COBS.value,
        CoreComInterfaces.SERIAL_QEMU.value,
    ]:
        # For a serial communication interface, there are some configuration values like
        # baud rate and serial port which need to be set once but are expected to stay
        # the same for a given machine. Therefore, we use a JSON file to store and extract
        # those values
        cfg = SerialCfg(baud_rate=0, com_if_id=com_if_key, serial_port="")
        cfg = default_serial_cfg_baud_and_port_setup(cfg_path, cfg)
        return SerialConfigCommon(com_if_key=com_if_key, config_path=cfg_path, serial_cfg=cfg)
    else:
        return None


def create_com_interface_default(
    config: TcpipConfig | SerialConfigCommon | DummyConfig,
) -> ComInterface | None:
    """Return the desired communication interface object

    :param cfg: Generic configuration
    :return:
    """
    if config.com_if_key == "":
        _LOGGER.warning("COM Interface key string is empty. Using dummy COM interface")
    try:
        return __create_com_if(config)
    except ConnectionRefusedError:
        _LOGGER.exception("TCP/IP connection refused")
        if config.com_if_key == CoreComInterfaces.UDP.value:
            _LOGGER.warning("Make sure that a UDP server is running")
        if config.com_if_key == CoreComInterfaces.TCP.value:
            _LOGGER.warning("Make sure that a TCP server is running")
        sys.exit(1)
    except OSError:
        _LOGGER.exception("Error setting up communication interface")
        sys.exit(1)


def __create_com_if(cfg: TcpipConfig | SerialConfigCommon | DummyConfig) -> ComInterface | None:
    from tmtccmd.com.dummy import DummyInterface

    if (
        cfg.com_if_key == CoreComInterfaces.UDP.value
        or cfg.com_if_key == CoreComInterfaces.TCP.value
    ):
        assert isinstance(cfg, TcpipConfig)
        communication_interface = create_default_tcpip_interface(cast(TcpipConfig, cfg))
    elif cfg.com_if_key in [
        CoreComInterfaces.SERIAL_DLE.value,
        CoreComInterfaces.SERIAL_COBS.value,
    ]:
        assert isinstance(cfg, SerialConfigCommon)
        communication_interface = create_default_serial_interface(
            com_if_key=cfg.com_if_key,
            serial_cfg=cfg.serial_cfg,
        )
    else:
        communication_interface = DummyInterface()
    if communication_interface is None:
        _LOGGER.warning("Invalid communication interface, is None")
        return communication_interface
    communication_interface.initialize()
    return communication_interface


def default_tcpip_config(
    com_if_key: str,
    tcpip_type: TcpIpType,
    cfg_path: str,
    space_packet_ids: Sequence[PacketId] | None,
) -> TcpipConfig | None:
    """Default setup for TCP/IP communication interfaces. This intantiates all required data in the
    globals manager so a TCP/IP communication interface can be built with
    :func:`create_default_tcpip_interface`

    :param com_if_key:
    :param tcpip_type:
    :param json_cfg_path:
    :param space_packet_ids:       Required if the TCP com interface needs to parse space packets
    :return:
    """

    send_addr = None
    if cfg_path.endswith("json") or cfg_path.endswith("toml"):
        if tcpip_type == TcpIpType.UDP:
            send_addr = determine_udp_send_address(cfg_path=cfg_path)
        elif tcpip_type == TcpIpType.TCP:
            send_addr = determine_tcp_send_address(cfg_path=cfg_path)
        else:
            raise ValueError("Invalid TCP/IP server type")
    if send_addr is None:
        return None
    cfg = TcpipConfig(
        com_if_key=com_if_key,
        if_type=tcpip_type,
        config_path=cfg_path,
        send_addr=send_addr,
        space_packet_ids=space_packet_ids,
    )
    return cfg


def default_serial_cfg_baud_and_port_setup(com_if_id: str, cfg_path: str) -> SerialCfg:
    """Default setup for serial interfaces.

    :param json_cfg_path:
    :param cfg: The baud and serial port parameter will be set in this dataclass
    :return:
    """
    baud_rate = determine_baud_rate(cfg_path=cfg_path)
    serial_port = determine_com_port(cfg_path=cfg_path)
    return SerialCfg(com_if_id, serial_port, baud_rate)


def create_default_tcpip_interface(tcpip_cfg: TcpipConfig) -> ComInterface | None:
    """Create a default serial interface. Requires a certain set of global variables set up. See
    :py:func:`default_tcpip_cfg_setup` for more details.

    :param tcpip_cfg: Configuration parameters
    :return:
    """
    communication_interface = None
    if tcpip_cfg.com_if_key == CoreComInterfaces.UDP.value:
        communication_interface = UdpClient(
            com_if_id=tcpip_cfg.com_if_key,
            send_address=tcpip_cfg.send_addr,
            recv_addr=tcpip_cfg.recv_addr,
        )
    elif tcpip_cfg.com_if_key == CoreComInterfaces.TCP.value:
        assert tcpip_cfg.space_packet_ids is not None
        communication_interface = TcpSpacepacketsClient(
            com_if_id=tcpip_cfg.com_if_key,
            space_packet_ids=tcpip_cfg.space_packet_ids,
            inner_thread_delay=0.5,
            target_address=tcpip_cfg.send_addr,
        )
    return communication_interface


def create_default_serial_interface(com_if_key: str, serial_cfg: SerialCfg) -> ComInterface | None:
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
