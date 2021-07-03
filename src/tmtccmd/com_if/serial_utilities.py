import json

import serial
import serial.tools.list_ports
from tmtccmd.utility.logger import get_console_logger
from tmtccmd.utility.json_handler import check_json_file, JsonKeyNames

LOGGER = get_console_logger()


def determine_baud_rate(json_cfg_path: str) -> int:
    """
    Determine baud rate. Tries to read from JSON first. If the baud rate is not contained
    in the config JSON, prompt it from user instead with the option to store value in JSON file.
    :return: Determined baud rate
    """
    baud_rate = 0
    prompt_baud_rate = False
    if not check_json_file(json_cfg_path=json_cfg_path):
        prompt_baud_rate = True

    if not prompt_baud_rate:
        with open(json_cfg_path, "r") as read:
            try:
                load_data = json.load(read)
                baud_rate = load_data[JsonKeyNames.SERIAL_BAUDRATE.value]
            except KeyError:
                prompt_baud_rate = True

    if prompt_baud_rate:
        while True:
            baud_rate = input("Please enter the baudrate for the serial protocol: ")
            if baud_rate.isdigit():
                baud_rate = int(baud_rate)
                break
            else:
                print("Invalid baud rate specified, try again.")
        save_to_json = input("Do you want to store baud rate to the configuration file? (y/n): ")
        if save_to_json.lower() in ['y', "yes", "1"]:
            with open(json_cfg_path, "r+") as file:
                data = json.load(file)
                data[JsonKeyNames.SERIAL_BAUDRATE.value] = baud_rate
                file.seek(0)
                json.dump(data, file, indent=4)
            LOGGER.info("Baud rate was stored to the JSON file config/tmtcc_config.json")
            LOGGER.info("Delete this file or edit it manually to change the baud rate")
    return baud_rate


def determine_com_port(json_cfg_path: str) -> str:
    """
    Determine serial port. Tries to read from JSON first. If the com port is not contained
    in the config JSON, prompt it from user instead with the option to store value in JSON file.
    :return: Determined serial port
    """
    reconfigure_com_port = False
    com_port = ""
    if not check_json_file(json_cfg_path=json_cfg_path):
        reconfigure_com_port = True

    with open(json_cfg_path, "r") as read:
        try:
            load_data = json.load(read)
            com_port = load_data[JsonKeyNames.SERIAL_PORT.value]
        except KeyError:
            reconfigure_com_port = True
        if not check_port_validity(com_port):
            reconfigure = input(
                "COM port from configuration file not contained within serial"
                "port list. Reconfigure serial port? [y/n]: ")
            if reconfigure.lower() in ['y', "yes", "1"]:
                reconfigure_com_port = True

    if reconfigure_com_port:
        com_port = prompt_com_port()
        save_to_json = input("Do you want to store serial port to the"
                             " configuration file? (y/n): ")
        if save_to_json.lower() in ['y', "yes"]:
            with open(json_cfg_path, "r+") as file:
                data = json.load(file)
                data[JsonKeyNames.SERIAL_PORT.value] = com_port
                file.seek(0)
                json.dump(data, file, indent=4)
            LOGGER.info("Serial port was stored to the JSON file config/tmtcc_config.json")
            LOGGER.info("Delete this file or edit it manually to change serial port")
    return com_port


def prompt_com_port() -> str:
    while True:
        com_port = input(
            "Configuring serial port. Please enter COM Port"
            "(enter h to display list of COM ports): ")
        if com_port == 'h':
            ports = serial.tools.list_ports.comports()
            for port, desc, hwid in sorted(ports):
                print("{}: {} [{}]".format(port, desc, hwid))
        else:
            if not check_port_validity(com_port):
                print("Serial port not in list of available serial ports. Try again? [y/n]")
                try_again = input()
                if try_again.lower() in ['y', "yes"]:
                    continue
                else:
                    break
            else:
                break
    return com_port


def check_port_validity(com_port_to_check: str) -> bool:
    port_list = []
    ports = serial.tools.list_ports.comports()
    for port, desc, hwid in sorted(ports):
        port_list.append(port)
    if com_port_to_check not in port_list:
        return False
    return True
