import json
import os
import socket
import struct
from typing import Tuple

from tmtccmd.core.definitions import ethernet_address_t
from tmtccmd.utility.tmtcc_logger import get_logger

LOGGER = get_logger()


def determine_ip_addresses() -> Tuple[ethernet_address_t, ethernet_address_t]:
    send_address = ()
    recv_address = ()
    reconfigure_ip_address = False
    if os.path.isfile("config/tmtcc_config.json"):
        with open("config/tmtcc_config.json", "r") as write:
            load_data = json.load(write)
            if "DEST_IP_ADDRESS" not in load_data or "DEST_PORT" not in load_data \
                    or "RECV_IP_ADDRESS" not in load_data or "RECV_PORT" not in load_data:
                reconfigure_ip_address = True
            else:
                send_address = load_data["DEST_IP_ADDRESS"], int(load_data["DEST_PORT"])
                recv_address = load_data["RECV_IP_ADDRESS"], int(load_data["RECV_PORT"])
    else:
        reconfigure_ip_address = True

    if reconfigure_ip_address:
        send_address, recv_address = prompt_ip_addresses()
        save_to_json = input("Do you want to store the ethernet configuration? [y/n]: ")
        if save_to_json.lower() in ['y', "yes"]:

            if os.path.isfile("config/tmtcc_config.json"):
                # Load existing JSON config and update it
                file_open_flag = "r+"
            else:
                # Create new JSON config
                file_open_flag = "w"

            with open("config/tmtcc_config.json", file_open_flag) as json_file:
                json_dict = dict()
                json_dict["DEST_IP_ADDRESS"] = send_address[0]
                json_dict["DEST_PORT"] = send_address[1]
                json_dict["RECV_IP_ADDRESS"] = recv_address[0]
                json_dict["RECV_PORT"] = recv_address[1]
                json.dump(json_dict, json_file, indent=4)

            LOGGER.info("IP addresses were stored to the JSON file config/tmtcc_config.json.")
            LOGGER.info("Delete this file or edit it manually to change the loaded IP addresses.")
    return send_address, recv_address


def prompt_ip_addresses():
    send_address = ()
    recv_address = ()
    while True:
        send_ip = input(
            "Configuring destination IP address. Please enter the IP address (\"localhost\" is valid): "
        )

        check_ip = True
        if send_ip == "localhost":
            send_ip = socket.inet_ntoa(struct.pack('!L', socket.INADDR_LOOPBACK))
            check_ip = False

        if check_ip:
            try:
                socket.inet_aton(str(send_ip))
            except socket.error:
                LOGGER.warning("Invalid IP address format!")
                continue

        send_port = input(
            "Please enter destination port: "
        )
        send_address = (send_ip, int(send_port))

        LOGGER.info(f"Specified destination IP address: {send_ip}")
        LOGGER.info(f"Specified destination port: {send_port}")

        confirm = input("Please confirm selection [y/n]: ")
        if not confirm.lower() in ['y', "yes", 1]:
            continue
        break

    while True:
        receive_ip = input(
            f"Configuring receive IP address. {os.linesep}"
            "Please enter the IP address (use \"any\" or leave empty to bind to any): "
        )

        check_ip = True
        if receive_ip == "any":
            receive_ip = socket.inet_ntoa(struct.pack('!L', socket.INADDR_ANY))
            check_ip = False

        if check_ip:
            try:
                socket.inet_aton(receive_ip)
            except socket.error:
                LOGGER.warning("Invalid IP address format!")
                continue

        receive_port = input("Please enter receive port: ")

        recv_address = (receive_ip, int(receive_port))

        LOGGER.info(f"Specified receive IP address: {receive_ip}")
        LOGGER.info(f"Specified receive destination port: {receive_port}")

        confirm = input("Please confirm selection [y/n]: ")
        if not confirm.lower() in ['y', "yes", 1]:
            continue
        break
    return send_address, recv_address
