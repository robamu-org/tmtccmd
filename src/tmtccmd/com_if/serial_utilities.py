import os
import json

import serial
import serial.tools.list_ports


def determine_baud_rate() -> int:
    prompt_baud_rate = False
    baud_rate = 0
    if os.path.isfile("config/tmtcc_config.json"):
        with open("config/tmtcc_config.json", "r") as write:
            try:
                load_data = json.load(write)
                baud_rate = load_data["BAUD_RATE"]
            except KeyError:
                prompt_baud_rate = True
    else:
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
            with open("config/tmtcc_config.json", "r+") as file:
                data = json.load(file)
                data.update(dict(BAUD_RATE=baud_rate))
                file.seek(0)
                json.dump(data, file)
    return baud_rate


def determine_com_port() -> str:
    reconfigure_com_port = False
    com_port = ""

    if os.path.isfile("config/tmtcc_config.json"):
        with open("config/tmtcc_config.json", "r") as write:
            try:
                load_data = json.load(write)
                com_port = load_data["COM_PORT"]
            except KeyError:
                reconfigure_com_port = True
            if not check_port_validity(com_port):
                reconfigure = input(
                    "COM port from configuration file not contained within serial"
                    "port list. Reconfigure serial port? [y/n]: ")
                if reconfigure.lower() in ['y', "yes", "1"]:
                    write.close()
                    os.remove("config/tmtcc_config.json")
                    reconfigure_com_port = True
    else:
        reconfigure_com_port = True

    if reconfigure_com_port:
        com_port = prompt_com_port()
        save_to_json = input("Do you want to store serial port to the"
                             "configuration file? (y/n): ")
        if save_to_json.lower() in ['y', "yes"]:
            with open("config/tmtcc_config.json", "r+") as file:
                data = json.load(file)
                data.update(dict(COM_PORT=com_port))
                file.seek(0)
                json.dump(data, file)
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
