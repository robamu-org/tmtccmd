import json
import os
import enum
from tmtccmd.utility.logger import get_console_logger

LOGGER = get_console_logger()


class JsonKeyNames(enum.Enum):
    COM_IF = "com_if"
    TCPIP_UDP_DEST_IP_ADDRESS = "tcpip_udp_ip_addr"
    TCPIP_UDP_DEST_PORT = "tcpip_udp_port"
    TCPIP_UDP_RECV_IP_ADDRESS = "tcpip_udp_recv_addr"
    TCPIP_UDP_RECV_PORT = "tcpip_udp_recv_port"
    TCPIP_UDP_RECV_MAX_SIZE = "tcpip_udp_recv_max_size"

    TCPIP_TCP_DEST_IP_ADDRESS = "tcpip_tcp_ip_addr"
    TCPIP_TCP_DEST_PORT = "tcpip_tcp_port"
    TCPIP_TCP_RECV_MAX_SIZE = "tcpip_tcp_recv_max_size"

    SERIAL_BAUDRATE = "serial_baudrate"
    SERIAL_PORT = "serial_port"
    SERIAL_HINT = "serial_hint"


def check_json_file(json_cfg_path: str) -> bool:
    """The check JSON file and return whether it was valid or not. A JSON file is invalid
    if it does not exist or the format ins invalid.
    :return: True if JSON file is valid, False if not and a new one was created at the specified path
    """
    if json_cfg_path == "":
        json_cfg_path = "tmtc_config.json"
    if not os.path.isfile(json_cfg_path):
        with open(json_cfg_path, "w") as file:
            load_data = dict()
            json.dump(load_data, file)
            print(
                f"Configuration JSON {json_cfg_path} did not exist, created a new one."
            )
            return False
    else:
        with open(json_cfg_path, "r+") as file:
            try:
                json.load(file)
            except json.decoder.JSONDecodeError:
                LOGGER.warning(
                    "JSON decode error, file format might be invalid. Replacing JSON"
                )
                file.flush()
                file.truncate(0)
                file.seek(0)
                void_data = dict()
                json.dump(void_data, file)
                return False
    return True


def save_to_json_with_prompt(
    key: str, value: any, name: str, json_cfg_path: str, json_obj: any
) -> bool:
    logger = get_console_logger()
    save_to_json = input(
        f"Do you want to store the {name} to the configuration file? (y/n): "
    )
    if save_to_json.lower() in ["y", "yes"]:
        json_obj[key] = value
        logger.info(f"The {name} was stored to the JSON file {json_cfg_path}")
        logger.info("Delete this file or edit it manually to change it")
        return True
    return False
