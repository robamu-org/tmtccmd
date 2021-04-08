import json

from tmtccmd.utility.tmtcc_logger import get_logger

from tmtccmd.utility.json_handler import check_json_file, JsonKeyNames
LOGGER = get_logger()


def determine_com_if(integer_to_string_dict: dict) -> int:
    prompt_com_if = False
    if not check_json_file():
        prompt_com_if = True

    if not prompt_com_if:
        with open("config/tmtcc_config.json", "r") as read:
            com_if_string = ""
            try:
                load_data = json.load(read)
                com_if_string = load_data[JsonKeyNames.COM_IF.value]
            except KeyError:
                prompt_com_if = True
            com_if_value = convert_com_if_string_to_integer(com_if_string)
            if com_if_value != -1:
                return com_if_value
            else:
                prompt_com_if = True
    if prompt_com_if:
        while True:
            for integer_rep, string_rep in integer_to_string_dict.items():
                print(f"{integer_rep}: {string_rep}")
            com_if_key = input("Please enter the desired communication interface by key: ")
            if not com_if_key.isdigit():
                print("Key is not a digit, try again")
                continue
            com_if_key = int(com_if_key)
            if com_if_key in integer_to_string_dict:
                com_if_string = integer_to_string_dict[com_if_key]
                break
            else:
                print("Invalid key, try again.")
        save_to_json = input("Do you want to store the communication interface? (y/n): ")
        if save_to_json.lower() in ['y', "yes", "1"]:
            with open("config/tmtcc_config.json", "r+") as file:
                data = json.load(file)
                data[JsonKeyNames.COM_IF.value] = com_if_string
                file.seek(0)
                json.dump(data, file, indent=4)
            LOGGER.info(
                "Communication interface was stored in the JSON file config/tmtcc_config.json"
            )
            LOGGER.info("Delete this file or edit it manually to edit the communication interface")
        return com_if_key


def convert_com_if_string_to_integer(com_if_string: str) -> int:
    from tmtccmd.core.definitions import CoreComInterfacesString, CoreComInterfaces
    for com_if_int, com_if_string_in_dict in CoreComInterfacesString.items():
        if com_if_string == com_if_string_in_dict:
            return com_if_int
    return -1
