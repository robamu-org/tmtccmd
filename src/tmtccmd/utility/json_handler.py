import json
import os
import enum
from tmtccmd.utility.logger import get_console_logger

LOGGER = get_console_logger()


class JsonKeyNames(enum.Enum):
    COM_IF = "COM_IF_KEY"
    TCPIP_UDP_DEST_IP_ADDRESS = "TCPIP_UDP_DEST_IP_ADDRESS"
    TCPIP_UDP_DEST_PORT = "TCPIP_UDP_DEST_PORT"
    TCPIP_UDP_RECV_IP_ADDRESS = "TCPIP_UDP_RECV_IP_ADDRESS"
    TCPIP_UDP_RECV_PORT = "TCPIP_UDP_RECV_PORT"
    TCPIP_UDP_RECV_MAX_SIZE = "TCPIP_UDP_RECV_MAX_SIZE"

    TCPIP_TCP_DEST_IP_ADDRESS = "TCPIP_TCP_DEST_IP_ADDRESS"
    TCPIP_TCP_DEST_PORT = "TCPIP_TCP_DEST_PORT"
    TCPIP_TCP_RECV_MAX_SIZE = "TCPIP_UDP_RECV_MAX_SIZE"

    SERIAL_BAUDRATE = "SERIAL_BAUDRATE"
    SERIAL_PORT = "SERIAL_PORT"


def check_json_file(json_cfg_path: str) -> bool:
    """
    The check JSON file and return whether it was valid or not. A JSON file is invalid
    if it does not exist or the format ins invalid.
    :return: True if JSON file is valid, False if not and a new one was created at the specified path
    """
    if json_cfg_path == "":
        json_cfg_path = "tmtc_config.json"
    if not os.path.isfile(json_cfg_path):
        with open(json_cfg_path, "w") as file:
            load_data = dict()
            json.dump(load_data, file)
            print(f"Configuration JSON {json_cfg_path} did not exist, created a new one.")
            return False
    else:
        with open(json_cfg_path, "r+") as file:
            try:
                json.load(file)
            except json.decoder.JSONDecodeError:
                LOGGER.warning("JSON decode error, file format might be invalid. Replacing JSON")
                file.flush()
                file.truncate(0)
                file.seek(0)
                void_data = dict()
                json.dump(void_data, file)
                return False
    return True
