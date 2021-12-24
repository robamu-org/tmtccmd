import sys
from typing import Optional, Tuple

from tmtccmd.config.definitions import CoreGlobalIds, CoreComInterfaces
from tmtccmd.core.globals_manager import get_global, update_global
from tmtccmd.com_if.com_interface_base import CommunicationInterface
from tmtccmd.com_if.serial_com_if import (
    SerialConfigIds,
    SerialCommunicationType,
    SerialComIF,
)
from tmtccmd.com_if.serial_utilities import determine_com_port, determine_baud_rate
from tmtccmd.com_if.tcpip_utilities import TcpIpConfigIds, TcpIpType
from tmtccmd.utility.logger import get_console_logger
from tmtccmd.utility.tmtc_printer import TmTcPrinter
from tmtccmd.com_if.tcpip_udp_com_if import TcpIpUdpComIF
from tmtccmd.com_if.tcpip_tcp_com_if import TcpIpTcpComIF, TcpCommunicationType

LOGGER = get_console_logger()


def create_communication_interface_default(
    com_if_key: str,
    tmtc_printer: TmTcPrinter,
    json_cfg_path: str,
    space_packet_ids: Tuple[int] = (0,),
) -> Optional[CommunicationInterface]:
    """Return the desired communication interface object

    :param com_if_key:
    :param tmtc_printer:
    :param json_cfg_path:
    TODO: List of packet IDs?
    :param space_packet_id: Can be used by communication interfaces as a start marker (e.g. TCP)
    :return:
    """
    from tmtccmd.com_if.dummy_com_if import DummyComIF
    from tmtccmd.com_if.qemu_com_if import QEMUComIF

    try:
        if (
            com_if_key == CoreComInterfaces.TCPIP_UDP.value
            or com_if_key == CoreComInterfaces.TCPIP_TCP.value
        ):
            communication_interface = create_default_tcpip_interface(
                com_if_key=com_if_key,
                json_cfg_path=json_cfg_path,
                tmtc_printer=tmtc_printer,
                space_packet_ids=space_packet_ids,
            )
        elif (
            com_if_key == CoreComInterfaces.SERIAL_DLE.value
            or com_if_key == CoreComInterfaces.SERIAL_FIXED_FRAME.value
        ):
            communication_interface = create_default_serial_interface(
                com_if_key=com_if_key,
                tmtc_printer=tmtc_printer,
                json_cfg_path=json_cfg_path,
            )
        elif com_if_key == CoreComInterfaces.SERIAL_QEMU.value:
            serial_cfg = get_global(CoreGlobalIds.SERIAL_CONFIG)
            serial_timeout = serial_cfg[SerialConfigIds.SERIAL_TIMEOUT]
            communication_interface = QEMUComIF(
                tmtc_printer=tmtc_printer,
                serial_timeout=serial_timeout,
                ser_com_type=SerialCommunicationType.DLE_ENCODING,
            )
            dle_max_queue_len = serial_cfg[SerialConfigIds.SERIAL_DLE_QUEUE_LEN]
            dle_max_frame_size = serial_cfg[SerialConfigIds.SERIAL_DLE_MAX_FRAME_SIZE]
            communication_interface.set_dle_settings(
                dle_max_queue_len, dle_max_frame_size, serial_timeout
            )
        else:
            communication_interface = DummyComIF(
                com_if_key=com_if_key, tmtc_printer=tmtc_printer
            )
        if communication_interface is None:
            return communication_interface
        if not communication_interface.valid:
            LOGGER.warning("Invalid communication interface!")
            return None
        communication_interface.initialize()
        return communication_interface
    except ConnectionRefusedError:
        LOGGER.exception(f"TCP/IP connection refused")
        if com_if_key == CoreComInterfaces.TCPIP_UDP.value:
            LOGGER.warning("Make sure that a UDP server is running")
        if com_if_key == CoreComInterfaces.TCPIP_TCP.value:
            LOGGER.warning("Make sure that a TCP server is running")
        sys.exit(1)
    except (IOError, OSError):
        LOGGER.exception(f"Error setting up communication interface")
        sys.exit(1)


def default_tcpip_cfg_setup(
    tcpip_type: TcpIpType, json_cfg_path: str, space_packet_ids: Tuple[int] = (0,)
):
    """Default setup for TCP/IP communication interfaces. This intantiates all required data in the
    globals manager so a TCP/IP communication interface can be built with
    :func:`create_default_tcpip_interface`
    :param tcpip_type:
    :param json_cfg_path:
    :param space_packet_id:       Required if the TCP com interface needs to parse space packets
    :return:
    """
    from tmtccmd.com_if.tcpip_utilities import (
        determine_udp_send_address,
        determine_tcp_send_address,
        determine_recv_buffer_len,
    )

    update_global(CoreGlobalIds.USE_ETHERNET, True)
    recv_tuple = None
    if tcpip_type == TcpIpType.UDP:
        send_tuple = determine_udp_send_address(json_cfg_path=json_cfg_path)
    elif tcpip_type == TcpIpType.TCP:
        send_tuple = determine_tcp_send_address(json_cfg_path=json_cfg_path)
    else:
        send_tuple = ()
    max_recv_buf_size = determine_recv_buffer_len(
        json_cfg_path=json_cfg_path, tcpip_type=tcpip_type
    )
    ethernet_cfg_dict = get_global(CoreGlobalIds.ETHERNET_CONFIG)
    ethernet_cfg_dict.update({TcpIpConfigIds.SEND_ADDRESS: send_tuple})
    ethernet_cfg_dict.update({TcpIpConfigIds.RECV_ADDRESS: recv_tuple})
    ethernet_cfg_dict.update({TcpIpConfigIds.RECV_MAX_SIZE: max_recv_buf_size})
    if space_packet_ids == (0,) and tcpip_type == TcpIpType.TCP:
        LOGGER.warning(
            "TCP communication interface without any specified space packet ID might not work!"
        )
    ethernet_cfg_dict.update({TcpIpConfigIds.SPACE_PACKET_ID: space_packet_ids})
    update_global(CoreGlobalIds.ETHERNET_CONFIG, ethernet_cfg_dict)


def default_serial_cfg_setup(com_if_key: str, json_cfg_path: str):
    """Default setup for serial interfaces

    :param com_if_key:
    :param json_cfg_path:
    :return:
    """
    baud_rate = determine_baud_rate(json_cfg_path=json_cfg_path)
    serial_port = determine_com_port(json_cfg_path=json_cfg_path)
    set_up_serial_cfg(
        json_cfg_path=json_cfg_path,
        com_if_key=com_if_key,
        baud_rate=baud_rate,
        com_port=serial_port,
    )


def create_default_tcpip_interface(
    com_if_key: str,
    tmtc_printer: TmTcPrinter,
    json_cfg_path: str,
    space_packet_ids: Tuple[int] = (0,),
) -> Optional[CommunicationInterface]:
    """Create a default serial interface. Requires a certain set of global variables set up. See
    :func:`default_tcpip_cfg_setup` for more details.

    :param com_if_key:
    :param tmtc_printer:
    :param json_cfg_path:
    :param space_packet_ids: Two byte packet IDs which is used by TCP to parse space packets
    :return:
    """
    communication_interface = None
    if com_if_key == CoreComInterfaces.TCPIP_UDP.value:
        default_tcpip_cfg_setup(tcpip_type=TcpIpType.UDP, json_cfg_path=json_cfg_path)
    elif com_if_key == CoreComInterfaces.TCPIP_TCP.value:
        default_tcpip_cfg_setup(
            tcpip_type=TcpIpType.TCP,
            json_cfg_path=json_cfg_path,
            space_packet_ids=space_packet_ids,
        )
    ethernet_cfg_dict = get_global(CoreGlobalIds.ETHERNET_CONFIG)
    send_addr = ethernet_cfg_dict[TcpIpConfigIds.SEND_ADDRESS]
    recv_addr = ethernet_cfg_dict[TcpIpConfigIds.RECV_ADDRESS]
    max_recv_size = ethernet_cfg_dict[TcpIpConfigIds.RECV_MAX_SIZE]
    init_mode = get_global(CoreGlobalIds.MODE)
    space_packet_id = ethernet_cfg_dict[TcpIpConfigIds.SPACE_PACKET_ID]
    if com_if_key == CoreComInterfaces.TCPIP_UDP.value:
        communication_interface = TcpIpUdpComIF(
            com_if_key=com_if_key,
            tm_timeout=get_global(CoreGlobalIds.TM_TIMEOUT),
            tc_timeout_factor=get_global(CoreGlobalIds.TC_SEND_TIMEOUT_FACTOR),
            send_address=send_addr,
            recv_addr=recv_addr,
            max_recv_size=max_recv_size,
            tmtc_printer=tmtc_printer,
            init_mode=init_mode,
        )
    elif com_if_key == CoreComInterfaces.TCPIP_TCP.value:
        communication_interface = TcpIpTcpComIF(
            com_if_key=com_if_key,
            com_type=TcpCommunicationType.SPACE_PACKETS,
            space_packet_ids=space_packet_ids,
            tm_timeout=get_global(CoreGlobalIds.TM_TIMEOUT),
            tc_timeout_factor=get_global(CoreGlobalIds.TC_SEND_TIMEOUT_FACTOR),
            tm_polling_freqency=0.5,
            send_address=send_addr,
            max_recv_size=max_recv_size,
            tmtc_printer=tmtc_printer,
            init_mode=init_mode,
        )
    return communication_interface


def create_default_serial_interface(
    com_if_key: str, tmtc_printer: TmTcPrinter, json_cfg_path: str
) -> Optional[CommunicationInterface]:
    """Create a default serial interface. Requires a certain set of global variables set up. See
    :func:`set_up_serial_cfg` for more details.

    :param com_if_key:
    :param tmtc_printer:
    :param json_cfg_path:
    :return:
    """
    try:
        # For a serial communication interface, there are some configuration values like
        # baud rate and serial port which need to be set once but are expected to stay
        # the same for a given machine. Therefore, we use a JSON file to store and extract
        # those values
        if (
            com_if_key == CoreComInterfaces.SERIAL_DLE.value
            or com_if_key == CoreComInterfaces.SERIAL_FIXED_FRAME.value
            or com_if_key == CoreComInterfaces.SERIAL_QEMU.value
        ):
            default_serial_cfg_setup(com_if_key=com_if_key, json_cfg_path=json_cfg_path)
        serial_cfg = get_global(CoreGlobalIds.SERIAL_CONFIG)
        serial_baudrate = serial_cfg[SerialConfigIds.SERIAL_BAUD_RATE]
        serial_timeout = serial_cfg[SerialConfigIds.SERIAL_TIMEOUT]
        com_port = serial_cfg[SerialConfigIds.SERIAL_PORT]
        if com_if_key == CoreComInterfaces.SERIAL_DLE.value:
            ser_com_type = SerialCommunicationType.DLE_ENCODING
        else:
            ser_com_type = SerialCommunicationType.FIXED_FRAME_BASED
        communication_interface = SerialComIF(
            com_if_key=com_if_key,
            tmtc_printer=tmtc_printer,
            com_port=com_port,
            baud_rate=serial_baudrate,
            serial_timeout=serial_timeout,
            ser_com_type=ser_com_type,
        )
        if com_if_key == CoreComInterfaces.SERIAL_DLE:
            dle_max_queue_len = serial_cfg[SerialConfigIds.SERIAL_DLE_QUEUE_LEN]
            dle_max_frame_size = serial_cfg[SerialConfigIds.SERIAL_DLE_MAX_FRAME_SIZE]
            communication_interface.set_dle_settings(
                dle_max_queue_len, dle_max_frame_size, serial_timeout
            )
    except KeyError:
        LOGGER.warning("Serial configuration global not configured properly")
        return None
    return communication_interface


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
    :func:`create_default_serial_interface`
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
        LOGGER.warning("Invalid serial port specified!")
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
