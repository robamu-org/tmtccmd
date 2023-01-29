from __future__ import annotations
import json
import socket
import struct
import enum
from dataclasses import dataclass
from typing import Tuple

from tmtccmd.util.json import check_json_file, JsonKeyNames
from tmtccmd.logging import get_console_logger

LOGGER = get_console_logger()


DEFAULT_MAX_RECV_SIZE = 1500


@dataclass
class EthAddr:
    ip_addr: str
    port: int

    @property
    def to_tuple(self) -> Tuple[str, int]:
        return self.ip_addr, self.port

    @classmethod
    def from_tuple(cls, addr: Tuple[str, int]) -> EthAddr:
        return cls(addr[0], addr[1])


class TcpIpType(enum.Enum):
    TCP = enum.auto()
    UDP = enum.auto()
    UDP_RECV = enum.auto()


class TcpIpConfigIds(enum.Enum):
    from enum import auto

    SEND_ADDRESS = auto()
    RECV_ADDRESS = auto()
    RECV_MAX_SIZE = auto()
    # Used by TCP to detect start of space packets
    SPACE_PACKET_ID = auto()


def determine_udp_send_address(json_cfg_path: str) -> EthAddr:
    return determine_tcpip_address(
        tcpip_type=TcpIpType.UDP, json_cfg_path=json_cfg_path
    )


def determine_tcp_send_address(json_cfg_path: str) -> EthAddr:
    return determine_tcpip_address(
        tcpip_type=TcpIpType.TCP, json_cfg_path=json_cfg_path
    )


def determine_udp_recv_address(json_cfg_path: str) -> EthAddr:
    return determine_tcpip_address(
        tcpip_type=TcpIpType.UDP_RECV, json_cfg_path=json_cfg_path
    )


def determine_tcpip_address(tcpip_type: TcpIpType, json_cfg_path: str) -> EthAddr:
    addr = EthAddr("", 0)
    reconfigure_ip_address = False
    if not check_json_file(json_cfg_path=json_cfg_path):
        reconfigure_ip_address = True

    if tcpip_type == TcpIpType.TCP:
        json_key_address = JsonKeyNames.TCPIP_TCP_DEST_IP_ADDRESS.value
        json_key_port = JsonKeyNames.TCPIP_TCP_DEST_PORT.value
        info_string = "TCP destination"
    elif tcpip_type == TcpIpType.UDP:
        json_key_address = JsonKeyNames.TCPIP_UDP_DEST_IP_ADDRESS.value
        json_key_port = JsonKeyNames.TCPIP_UDP_DEST_PORT.value
        info_string = "UDP destination"
    elif tcpip_type == TcpIpType.UDP_RECV:
        json_key_address = JsonKeyNames.TCPIP_UDP_RECV_IP_ADDRESS.value
        json_key_port = JsonKeyNames.TCPIP_UDP_RECV_PORT.value
        info_string = "UDP receive destination"
    else:
        json_key_address = JsonKeyNames.TCPIP_UDP_DEST_IP_ADDRESS.value
        json_key_port = JsonKeyNames.TCPIP_UDP_DEST_PORT.value
        info_string = "UDP destination"

    with open(json_cfg_path, "r") as write:
        load_data = json.load(write)
        if json_key_address not in load_data or json_key_port not in load_data:
            reconfigure_ip_address = True
        else:
            ip_address = load_data[json_key_address]
            port = int(load_data[json_key_port])
            addr = EthAddr(ip_address, port)

    if reconfigure_ip_address:
        addr = prompt_ip_address(type_str=info_string)
        save_to_json = input(
            f"Do you want to store the {info_string} configuration? ([Y]/n): "
        )
        if save_to_json.lower() in ["y", "yes", ""]:
            with open(json_cfg_path, "r+") as file:
                json_dict = json.load(file)
                json_dict[json_key_address] = addr.ip_addr
                json_dict[json_key_port] = addr.port
                file.seek(0)
                json.dump(json_dict, file, indent=4)
            LOGGER.info(
                f"{info_string} was stored to the JSON file config/tmtcc_config.json."
            )
            LOGGER.info(
                "Delete this file or edit it manually to change the used addresses."
            )
        else:
            LOGGER.info(f"{info_string} configuration was not stored")
    return addr


def prompt_ip_address(type_str: str) -> EthAddr:
    """Prompt a valid IP address from the user"""
    addr = EthAddr("", 0)
    while True:
        ip_address = input(
            f"Configuring {type_str} IP address. "
            'Please enter the IP address ("localhost" and "any" is valid): '
        )

        check_ip = True
        if ip_address == "localhost":
            ip_address = socket.inet_ntoa(struct.pack("!L", socket.INADDR_LOOPBACK))
            check_ip = False
        elif ip_address == "any":
            ip_address = socket.inet_ntoa(struct.pack("!L", socket.INADDR_ANY))
            check_ip = False
        if check_ip:
            try:
                socket.inet_aton(str(ip_address))
            except socket.error:
                LOGGER.warning("Invalid IP address format!")
                continue

        port = input(f"Please enter {type_str} port: ")
        addr = EthAddr(ip_address, int(port))

        LOGGER.info(f"Specified {type_str} IP address: {ip_address}")
        LOGGER.info(f"Specified {type_str} port: {port}")

        confirm = input("Please confirm selection ([Y]/n): ")
        if not confirm.lower() in ["y", "yes", 1, ""]:
            continue
        break
    return addr


def determine_recv_buffer_len(json_cfg_path: str, tcpip_type: TcpIpType):
    recv_max_size = 0
    reconfigure_recv_buf_size = False
    if tcpip_type == TcpIpType.UDP:
        json_key = JsonKeyNames.TCPIP_UDP_RECV_MAX_SIZE.value
    elif tcpip_type == TcpIpType.TCP:
        json_key = JsonKeyNames.TCPIP_TCP_RECV_MAX_SIZE.value
    else:
        json_key = JsonKeyNames.TCPIP_UDP_RECV_MAX_SIZE.value

    if not check_json_file(json_cfg_path=json_cfg_path):
        reconfigure_recv_buf_size = True
    with open(json_cfg_path, "r") as write:
        load_data = json.load(write)
        if json_key not in load_data:
            reconfigure_recv_buf_size = True
        else:
            recv_max_size = load_data[json_key]
    if reconfigure_recv_buf_size:
        recv_max_size = prompt_recv_buffer_len(tcpip_type=tcpip_type)
        store_size = input(
            "Do you store the maximum receive size configuration? ([Y]/n): "
        )
        if store_size.lower() in ["y", "yes", "1", ""]:
            with open(json_cfg_path, "r+") as file:
                json_dict = json.load(file)
                json_dict[json_key] = recv_max_size
                file.seek(0)
                json.dump(json_dict, file, indent=4)
    return recv_max_size


def prompt_recv_buffer_len(tcpip_type: TcpIpType) -> int:
    if tcpip_type == TcpIpType.UDP:
        type_str = "UDP"
    else:
        type_str = "TCP"
    while True:
        recv_max_size = input(
            f"Please enter maximum receive size for {type_str} packets [1500 default]: "
        )
        if not recv_max_size:
            return DEFAULT_MAX_RECV_SIZE
        if not recv_max_size.isdigit():
            LOGGER.warning("Specified size is not a number.")
            continue
        else:
            try:
                recv_max_size = int(recv_max_size)
            except ValueError:
                LOGGER.warning("Specified input invalid")
                continue
            break
    return recv_max_size
