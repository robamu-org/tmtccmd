import json
import os
import socket
import struct
import enum
from typing import Tuple

from tmtccmd.core.definitions import ethernet_address_t
from tmtccmd.utility.json_handler import check_json_file
from tmtccmd.utility.tmtcc_logger import get_logger
from tmtccmd.utility.json_handler import JsonKeyNames

LOGGER = get_logger()


class TcpIpConfigIds(enum.Enum):
    from enum import auto
    SEND_ADDRESS = auto()
    RECV_ADDRESS = auto()
    RECV_MAX_SIZE = auto()


def determine_udp_address() -> ethernet_address_t:
    address_tuple = ()
    reconfigure_ip_address = False
    if not check_json_file():
        reconfigure_ip_address = True

    with open("config/tmtcc_config.json", "r") as write:
        load_data = json.load(write)
        if JsonKeyNames.TCPIP_DEST_IP_ADDRESS.value not in load_data or \
                JsonKeyNames.TCPIP_DEST_PORT.value not in load_data:
            reconfigure_ip_address = True
        else:
            ip_address = load_data[JsonKeyNames.TCPIP_DEST_IP_ADDRESS.value]
            port = int(load_data[JsonKeyNames.TCPIP_DEST_PORT.value])
            address_tuple = ip_address, port

    if reconfigure_ip_address:
        address_tuple = prompt_ip_address(type_str="UDP")
        save_to_json = input("Do you want to store the UDP address configuration? [y/n]: ")
        if save_to_json.lower() in ['y', "yes"]:
            with open("config/tmtcc_config.json", "r+") as file:
                json_dict = json.load(file)
                json_dict[JsonKeyNames.TCPIP_DEST_IP_ADDRESS.value] = address_tuple[0]
                json_dict[JsonKeyNames.TCPIP_DEST_PORT.value] = address_tuple[1]
                file.seek(0)
                json.dump(json_dict, file, indent=4)
            LOGGER.info(
                "Destination IP address was stored to the JSON file config/tmtcc_config.json."
            )
            LOGGER.info("Delete this file or edit it manually to change the loaded IP addresses.")
    return address_tuple


def prompt_ip_address(type_str: str) -> ethernet_address_t:
    address_tuple = ()
    while True:
        ip_address = input(
            f"Configuring {type_str} IP address. "
            "Please enter the IP address (\"localhost\" and \"any\" is valid): "
        )

        check_ip = True
        if ip_address == "localhost":
            send_ip = socket.inet_ntoa(struct.pack('!L', socket.INADDR_LOOPBACK))
            check_ip = False
        elif ip_address == "any":
            receive_ip = socket.inet_ntoa(struct.pack('!L', socket.INADDR_ANY))
            check_ip = False
        if check_ip:
            try:
                socket.inet_aton(str(send_ip))
            except socket.error:
                LOGGER.warning("Invalid IP address format!")
                continue

        send_port = input(
            f"Please enter {type_str} port: "
        )
        address_tuple = (send_ip, int(send_port))

        LOGGER.info(f"Specified destination IP address: {send_ip}")
        LOGGER.info(f"Specified destination port: {send_port}")

        confirm = input("Please confirm selection [y/n]: ")
        if not confirm.lower() in ['y', "yes", 1]:
            continue
        break
    return address_tuple


def determine_recv_buffer_len(udp: bool):
    recv_max_size = 0
    reconfigure_recv_buf_size = False
    if not check_json_file():
        reconfigure_recv_buf_size = True
    with open("config/tmtcc_config.json", "r") as write:
        load_data = json.load(write)
        if JsonKeyNames.TCPIP_RECV_MAX_SIZE.value not in load_data:
            reconfigure_recv_buf_size = True
        else:
            recv_max_size = load_data[JsonKeyNames.TCPIP_RECV_MAX_SIZE.value]
    if reconfigure_recv_buf_size:
        recv_max_size = prompt_recv_buffer_len(udp=udp)
        store_size = input("Do you store the maximum receive size configuration? [y/n]")
        if store_size.lower() in ["y", "yes", "1"]:
            with open("config/tmtcc_config.json", "r+") as file:
                json_dict = json.load(file)
                json_dict[JsonKeyNames.TCPIP_RECV_MAX_SIZE.value] = recv_max_size
                file.seek(0)
                json.dump(json_dict, file, indent=4)
    return recv_max_size


def prompt_recv_buffer_len(udp: bool) -> int:
    while True:
        if udp:
            type_str = "UDP"
        else:
            type_str = "TCP"
        recv_max_size = input(f"Please enter maximum receive size for {type_str} packets: ")
        if not recv_max_size.isdigit():
            LOGGER.warning("Specified size is not a number.")
            continue
        else:
            recv_max_size = int(recv_max_size)
            break
    return recv_max_size
