import json
import logging

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:
    import tomli as tomllib  # Fallback for older versions
from typing import TextIO

import serial
import serial.tools.list_ports

from tmtccmd.util.json import (
    JsonKeyNames,
    check_json_file,
)

_LOGGER = logging.getLogger(__name__)


def load_baud_rate_from_json(cfg_path: str) -> int | None:
    baud_rate = None
    if not check_json_file(json_cfg_path=cfg_path):
        return None
    with open(cfg_path) as read:
        try:
            load_data = json.load(read)
            baud_rate = load_data[JsonKeyNames.SERIAL_BAUDRATE.value]
        except KeyError:
            pass
    return baud_rate


def load_baud_rate_from_toml(cfg_path: str) -> int | None:
    baud_rate = None
    try:
        with open(cfg_path, "rb") as f:
            cfg = tomllib.load(f)
        baud_rate = cfg["serial"]["baud"]
    except (FileNotFoundError, KeyError, tomllib.TOMLDecodeError):
        pass
    return baud_rate


def load_serial_port_from_toml(cfg_path: str) -> str | None:
    baud_rate = None
    try:
        with open(cfg_path, "rb") as f:
            cfg = tomllib.load(f)
        baud_rate = cfg["serial"]["port"]
    except (FileNotFoundError, KeyError, tomllib.TOMLDecodeError):
        pass
    return baud_rate


def determine_baud_rate(cfg_path: str) -> int | None:
    """Determine baud rate. Tries to read from JSON first. If the baud rate is not contained
    in the config JSON, prompt it from user instead with the option to store value in JSON file.

    :return: Determined baud rate
    """
    baud_rate = None
    prompt_baud_rate = False
    if cfg_path.endswith("json"):
        baud_rate = load_baud_rate_from_json(cfg_path=cfg_path)
    elif cfg_path.endswith("toml"):
        baud_rate = load_baud_rate_from_toml(cfg_path=cfg_path)

    if baud_rate is None:
        with open(cfg_path) as read:
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
    return baud_rate


def determine_com_port(cfg_path: str) -> str | None:
    """Determine serial port. Tries to read from JSON first. If the serial port is not contained
    in the config JSON, prompt it from user instead with the option to store value in JSON file.

    :return: Determined serial port
    """
    reconfig_com_port = False
    if cfg_path.endswith("json"):
        if not check_json_file(json_cfg_path=cfg_path):
            reconfig_com_port = True
        with open(cfg_path, "r+") as json_file:
            com_port = __determine_com_port_with_json_file(
                json_file=json_file,
                reconfig_com_port=reconfig_com_port,
            )
    if cfg_path.endswith("toml"):
        com_port = load_serial_port_from_toml(cfg_path=cfg_path)
    return com_port


def __determine_com_port_with_json_file(json_file: TextIO, reconfig_com_port: bool) -> str | None:
    try_hint = False
    json_obj = json.load(json_file)
    com_port = ""
    if not reconfig_com_port:
        try_hint, com_port = __try_com_port_load(json_obj=json_obj)
    if try_hint:
        com_port = __try_hint_handling(
            json_obj=json_obj,
        )
        if com_port is None:
            return None

    if reconfig_com_port:
        com_port = prompt_com_port()
    return com_port


def __try_com_port_load(json_obj) -> tuple[bool, str]:
    try_hint = False
    com_port = ""
    try:
        com_port = json_obj[JsonKeyNames.SERIAL_PORT.value]
        _LOGGER.info(f"Loaded serial port {com_port} from JSON configuration file")
    except KeyError:
        try_hint = True
    return try_hint, com_port


def __try_hint_handling(json_obj) -> str | None:
    try:
        hint = json_obj[JsonKeyNames.SERIAL_HINT.value]
    except KeyError:
        hint = __prompt_hint_handling()

    com_port_found, com_port = find_com_port_from_hint(hint=hint)
    if com_port_found:
        _LOGGER.info(f"Found {com_port} based on hint {hint}")
    else:
        _LOGGER.info("No serial port found based on hint..")
    return com_port


def __prompt_hint_handling() -> str:
    hint = ""
    ports = serial.tools.list_ports.comports()
    prompt_hint = input(
        "No hint found in config JSON. Do you want to print the list of devices "
        "and then specify a hint based on it? ([Y]/n): "
    )
    if prompt_hint.lower() in ["y", "yes", "1", ""]:
        while True:
            _LOGGER.info("Found serial devices:")
            for port, desc, hwid in sorted(ports):
                print(f"{port}: {desc} [{hwid}]")
            hint = input("Specify hint: ")
    return hint


def find_com_port_from_hint(hint: str) -> tuple[bool, str]:
    """Find a COM port based on a hint string"""
    if hint == "":
        _LOGGER.warning("Invalid hint, is empty..")
        return False, ""
    ports = serial.tools.list_ports.comports()
    for port, desc, _hwid in sorted(ports):
        if hint in desc:
            return True, port
    return False, ""


def prompt_com_port() -> str:
    while True:
        com_port = input(
            "Configuring serial port. Please enter serial port"
            ' or "h" to display list of serial ports): '
        )
        if com_port == "h":
            ports = serial.tools.list_ports.comports()
            for port, desc, hwid in sorted(ports):
                print(f"{port}: {desc} [{hwid}]")
        else:
            if not check_port_validity(com_port):
                print("Serial port not in list of available serial ports. Try again? ([Y]/n)")
                try_again = input()
                if try_again.lower() in ["y", "yes", ""]:
                    continue
                else:
                    break
            else:
                break
    return com_port


def check_port_validity(com_port_to_check: str) -> bool:
    port_list = []
    ports = serial.tools.list_ports.comports()
    for port, _desc, _hwid in sorted(ports):
        port_list.append(port)
    return com_port_to_check in port_list
