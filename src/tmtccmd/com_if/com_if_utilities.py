import json

from tmtccmd.utility.logger import get_console_logger
from tmtccmd.utility.json_handler import check_json_file, JsonKeyNames
from tmtccmd.config.definitions import ComIFDictT

LOGGER = get_console_logger()


def determine_com_if(com_if_dict: ComIFDictT, json_cfg_path: str) -> str:
    do_prompt_com_if = False
    if not check_json_file(json_cfg_path=json_cfg_path):
        do_prompt_com_if = True
    if not do_prompt_com_if:
        with open(json_cfg_path, "r") as read:
            com_if_string = ""
            try:
                load_data = json.load(read)
                com_if_string = load_data[JsonKeyNames.COM_IF.value]
            except KeyError:
                do_prompt_com_if = True
            com_if_string = str(com_if_string)
    if do_prompt_com_if:
        com_if_string = prompt_com_if(com_if_dict=com_if_dict)
        save_to_json = input("Do you want to store the communication interface? (y/n): ")
        if save_to_json.lower() in ['y', "yes", "1"]:
            store_com_if_json(com_if_string=com_if_string, json_cfg_path=json_cfg_path)
    return com_if_string


def prompt_com_if(com_if_dict: dict) -> str:
    while True:
        com_if_list = []
        for index, com_if_value in enumerate(com_if_dict.items()):
            print(f"{index}: {com_if_value}")
            com_if_list.append(com_if_value)
        com_if_key = input("Please enter the desired communication interface by key: ")
        if not com_if_key.isdigit():
            print("Key is not a digit, try again")
            continue
        com_if_key = int(com_if_key)
        if com_if_key >= len(com_if_list):
            print("Key invalid, try again.")
            continue
        com_if_string = com_if_list[com_if_key][0]
        break
    return com_if_string


def store_com_if_json(com_if_string: str, json_cfg_path: str):
    with open(json_cfg_path, "r+") as file:
        data = json.load(file)
        data[JsonKeyNames.COM_IF.value] = com_if_string
        file.seek(0)
        json.dump(data, file, indent=4)
    LOGGER.info(
        f"Communication interface was stored in the JSON file {json_cfg_path}"
    )
    LOGGER.info("Delete this file or edit it manually to edit the communication interface")
