import json
import os
import enum
from tmtccmd.utility.tmtcc_logger import get_logger

LOGGER = get_logger()


class JsonKeyNames(enum.Enum):
    TCPIP_UDP_DEST_IP_ADDRESS = "TCPIP_UDP_DEST_IP_ADDRESS"
    TCPIP_UDP_DEST_PORT = "TCPIP_UDP_DEST_PORT"
    TCPIP_UDP_RECV_IP_ADDRESS = "TCPIP_UDP_RECV_IP_ADDRESS"
    TCPIP_UDP_RECV_PORT = "TCPIP_UDP_RECV_PORT"
    TCPIP_UDP_RECV_MAX_SIZE = "TCPIP_UDP_RECV_MAX_SIZE"

    SERIAL_BAUDRATE = "SERIAL_BAUDRATE"
    SERIAL_PORT = "SERIAL_PORT"


def check_json_file() -> bool:
    """
    The check JSON file and return whether it was valid or not. A JSON file is invalid
    if it does not exist or the format ins invalid.
    :return: True if JSON file is valid, False if not and a new one was created
    """
    if not os.path.isfile("config/tmtcc_config.json"):
        with open("config/tmtcc_config.json", "w") as file:
            load_data = dict()
            json.dump(load_data, file)
            print("Configuration JSON config/tmtcc_config.json did not exist, created a new one.")
            return False
    else:
        with open("config/tmtcc_config.json", "r+") as file:
            try:
                json.load(file)
            except json.decoder.JSONDecodeError:
                LOGGER.warning("JSON decode error, file format might be invalid. Replacing JSON")
                void_data = dict()
                json.dump(void_data, file)
                return False
    return True
