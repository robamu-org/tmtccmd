import sys
from typing import Union

from tmtccmd.core.definitions import CoreGlobalIds, CoreComInterfaces
from tmtccmd.core.globals_manager import get_global, update_global
from tmtccmd.com_if.com_interface_base import CommunicationInterface
from tmtccmd.com_if.serial_utilities import determine_com_port
from tmtccmd.utility.tmtcc_logger import get_logger
from tmtccmd.utility.tmtcc_tmtc_printer import TmTcPrinter


LOGGER = get_logger()


def create_communication_interface_default(
        com_if: int, tmtc_printer: TmTcPrinter
) -> Union[CommunicationInterface, None]:
    from tmtccmd.com_if.serial_com_if import SerialCommunicationType, SerialComIF
    from tmtccmd.com_if.dummy_com_if import DummyComIF
    from tmtccmd.com_if.ethernet_com_if import EthernetComIF
    from tmtccmd.com_if.qemu_com_if import QEMUComIF
    from tmtccmd.core.definitions import CoreGlobalIds
    from tmtccmd.core.globals_manager import get_global
    """
    Return the desired communication interface object
    :param tmtc_printer: TmTcPrinter object.
    :return: CommunicationInterface object
    """
    try:
        if com_if == CoreComInterfaces.EthernetUDP:
            from config.custom_definitions import EthernetConfig
            ethernet_cfg_dict = get_global(CoreGlobalIds.ETHERNET_CONFIG)
            send_addr = ethernet_cfg_dict[EthernetConfig.SEND_ADDRESS]
            rcv_addr = ethernet_cfg_dict[EthernetConfig.RECV_ADDRESS]
            communication_interface = EthernetComIF(
                tmtc_printer=tmtc_printer, tm_timeout=get_global(CoreGlobalIds.TM_TIMEOUT),
                tc_timeout_factor=get_global(CoreGlobalIds.TC_SEND_TIMEOUT_FACTOR),
                send_address=send_addr, receive_address=rcv_addr)
        elif com_if == CoreComInterfaces.Serial:
            from config.custom_definitions import SerialConfig
            serial_cfg = get_global(CoreGlobalIds.SERIAL_CONFIG)
            serial_baudrate = serial_cfg[SerialConfig.SERIAL_BAUD_RATE]
            serial_timeout = serial_cfg[SerialConfig.SERIAL_TIMEOUT]
            # Determine COM port, either extract from JSON file or ask from user.
            com_port = determine_com_port()
            communication_interface = SerialComIF(
                tmtc_printer=tmtc_printer, com_port=com_port, baud_rate=serial_baudrate,
                serial_timeout=serial_timeout,
                ser_com_type=SerialCommunicationType.DLE_ENCODING)
            dle_max_queue_len = serial_cfg[SerialConfig.SERIAL_DLE_QUEUE_LEN]
            dle_max_frame_size = serial_cfg[SerialConfig.SERIAL_DLE_MAX_FRAME_SIZE]
            communication_interface.set_dle_settings(dle_max_queue_len, dle_max_frame_size,
                                                     serial_timeout)
        elif com_if == CoreComInterfaces.QEMU:
            from config.custom_definitions import SerialConfig
            serial_cfg = get_global(CoreGlobalIds.SERIAL_CONFIG)
            serial_timeout = serial_cfg[SerialConfig.SERIAL_TIMEOUT]
            communication_interface = QEMUComIF(
                tmtc_printer=tmtc_printer, serial_timeout=serial_timeout,
                ser_com_type=SerialCommunicationType.DLE_ENCODING)
            dle_max_queue_len = serial_cfg[SerialConfig.SERIAL_DLE_QUEUE_LEN]
            dle_max_frame_size = serial_cfg[SerialConfig.SERIAL_DLE_MAX_FRAME_SIZE]
            communication_interface.set_dle_settings(
                dle_max_queue_len, dle_max_frame_size, serial_timeout)
        else:
            communication_interface = DummyComIF(tmtc_printer=tmtc_printer)
        if not communication_interface.valid:
            LOGGER.warning("Invalid communication interface!")
            sys.exit()
        communication_interface.initialize()
        return communication_interface
    except (IOError, OSError) as e:
        LOGGER.error("Error setting up communication interface")
        print(e)
        sys.exit(1)


def default_set_up_ethernet_cfg():
    from config.custom_definitions import EthernetConfig
    from tmtccmd.com_if.ethernet_utilities import determine_ip_addresses
    update_global(CoreGlobalIds.USE_ETHERNET, True)
    ethernet_cfg_dict = get_global(CoreGlobalIds.ETHERNET_CONFIG)
    # This will either load the addresses from a JSON file or prompt them from the user.
    send_addr, rcv_addr = determine_ip_addresses()
    ethernet_cfg_dict.update({EthernetConfig.SEND_ADDRESS: send_addr})
    ethernet_cfg_dict.update({EthernetConfig.RECV_ADDRESS: rcv_addr})
    update_global(CoreGlobalIds.ETHERNET_CONFIG, ethernet_cfg_dict)


def default_set_up_serial_cfg(com_if: CoreComInterfaces):
    from tmtccmd.com_if.serial_com_if import SerialCommunicationType
    from config.custom_definitions import SerialConfig
    update_global(CoreGlobalIds.USE_SERIAL, True)
    serial_cfg_dict = get_global(CoreGlobalIds.SERIAL_CONFIG)
    if com_if == CoreComInterfaces.Serial:
        com_port = determine_com_port()
    else:
        com_port = ""
    serial_cfg_dict.update({SerialConfig.SERIAL_PORT: com_port})
    serial_cfg_dict.update({SerialConfig.SERIAL_BAUD_RATE: 115200})
    serial_cfg_dict.update({SerialConfig.SERIAL_TIMEOUT: 0.01})
    serial_cfg_dict.update({SerialConfig.SERIAL_COMM_TYPE: SerialCommunicationType.DLE_ENCODING})
    serial_cfg_dict.update({SerialConfig.SERIAL_FRAME_SIZE: 256})
    serial_cfg_dict.update({SerialConfig.SERIAL_DLE_QUEUE_LEN: 25})
    serial_cfg_dict.update({SerialConfig.SERIAL_DLE_MAX_FRAME_SIZE: 1024})
    update_global(CoreGlobalIds.SERIAL_CONFIG, serial_cfg_dict)
