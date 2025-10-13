import json
import logging

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:
    import tomli as tomllib  # Fallback for older versions

from tmtccmd.config.defs import ComIfDictT, CoreComInterfaces
from tmtccmd.util.conf_util import wrapped_prompt
from tmtccmd.util.json import JsonKeyNames, check_json_file


def determine_com_if(com_if_dict: ComIfDictT, cfg_path: str, use_prompts: bool) -> str:
    if cfg_path.endswith("json"):
        com_if_string = load_com_if_from_json(cfg_path)
    elif cfg_path.endswith("toml"):
        com_if_string = load_com_if_from_toml(cfg_path)
    if com_if_string is None:
        if use_prompts:
            com_if_string = prompt_com_if(com_if_dict)
            save_to_json = wrapped_prompt(
                "Do you want to store the communication interface? ([Y]/n): "
            )
            if save_to_json.lower() in ["", "y", "yes", "1"]:
                store_com_if_json(com_if_string=com_if_string, json_cfg_path=cfg_path)
        else:
            return CoreComInterfaces.DUMMY.value
    return com_if_string


def load_com_if_from_json(cfg_path: str) -> str | None:
    if not check_json_file(cfg_path):
        return None
    with open(cfg_path) as read:
        com_if_string = ""
        try:
            load_data = json.load(read)
            com_if_string = load_data[JsonKeyNames.COM_IF.value]
        except KeyError:
            return None
        com_if_string = str(com_if_string)
    return com_if_string


def load_com_if_from_toml(cfg_path: str) -> str | None:
    if not cfg_path.endswith(".toml"):
        return None
    try:
        with open(cfg_path, "rb") as read:
            load_data = tomllib.load(read)
            com_if_string = load_data["tmtc"]["interface"]
    except (FileNotFoundError, KeyError, tomllib.TOMLDecodeError):
        return None
    return str(com_if_string)


def prompt_com_if(com_if_dict: ComIfDictT) -> str:
    com_if_string = ""
    while True:
        com_if_list = []
        print("List of available communication interfaces:")
        for index, (name, com_if_value) in enumerate(com_if_dict.items()):
            print(f"{index}: {com_if_value[0]}")
            com_if_list.append(name)
        com_if_key = wrapped_prompt("Please enter the desired communication interface by key: ")
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
    logger = logging.getLogger(__name__)
    logger.info(f"Communication interface was stored in the JSON file {json_cfg_path}")
    logger.info("Delete this file or edit it manually to edit the communication interface")
