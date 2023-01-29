import json

from tmtccmd.logging import get_console_logger
from tmtccmd.util.conf_util import wrapped_prompt
from tmtccmd.util.json import check_json_file, JsonKeyNames
from tmtccmd.config.defs import ComIfDictT, CoreComInterfaces

LOGGER = get_console_logger()


def determine_com_if(
    com_if_dict: ComIfDictT, json_cfg_path: str, use_prompts: bool
) -> str:
    do_prompt_com_if = False
    com_if_string = ""
    if not check_json_file(json_cfg_path):
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
    if do_prompt_com_if and use_prompts:
        com_if_string = prompt_com_if(com_if_dict)
        save_to_json = wrapped_prompt(
            "Do you want to store the communication interface? ([Y]/n): "
        )
        if save_to_json.lower() in ["", "y", "yes", "1"]:
            store_com_if_json(com_if_string=com_if_string, json_cfg_path=json_cfg_path)
    elif do_prompt_com_if and not use_prompts:
        return CoreComInterfaces.DUMMY.value
    return com_if_string


def prompt_com_if(com_if_dict: ComIfDictT) -> str:
    com_if_string = ""
    while True:
        com_if_list = []
        print("List of available communication interfaces:")
        for index, (name, com_if_value) in enumerate(com_if_dict.items()):
            print(f"{index}: {com_if_value[0]}")
            com_if_list.append(name)
        com_if_key = wrapped_prompt(
            "Please enter the desired communication interface by key: "
        )
        if not com_if_key.isdigit():
            print("Key is not a digit, try again")
            continue
        com_if_key = int(com_if_key)
        if com_if_key >= len(com_if_list):
            print("Key invalid, try again.")
            continue
        com_if_string = com_if_list[com_if_key]
        break
    return com_if_string


def store_com_if_json(com_if_string: str, json_cfg_path: str):
    with open(json_cfg_path, "r+") as file:
        data = json.load(file)
        data[JsonKeyNames.COM_IF.value] = com_if_string
        file.seek(0)
        json.dump(data, file, indent=4)
    LOGGER.info(f"Communication interface was stored in the JSON file {json_cfg_path}")
    LOGGER.info(
        "Delete this file or edit it manually to edit the communication interface"
    )
