from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.shortcuts import CompleteStyle
import prompt_toolkit
from tmtccmd.config.tmtc import OpCodeEntry, TmTcDefWrapper
from tmtccmd.logging import get_console_logger

LOGGER = get_console_logger()


def prompt_service(tmtc_defs: TmTcDefWrapper) -> str:
    service_adjustment = 20
    info_adjustment = 30
    horiz_line_num = service_adjustment + info_adjustment + 3
    horiz_line = horiz_line_num * "-"
    service_string = "Service".ljust(service_adjustment)
    info_string = "Information".ljust(info_adjustment)
    tmtc_defs.sort()
    while True:
        print(f" {horiz_line}")
        print(f"|{service_string} | {info_string}|")
        print(f" {horiz_line}")
        srv_completer = build_service_word_completer(tmtc_defs)
        for service_entry in tmtc_defs.defs.items():
            try:
                adjusted_service_entry = service_entry[0].ljust(service_adjustment)
                adjusted_service_info = service_entry[1][0].ljust(info_adjustment)
                print(f"|{adjusted_service_entry} | {adjusted_service_info}|")
            except AttributeError:
                LOGGER.warning(
                    f"Error handling service entry {service_entry[0]}. Skipping.."
                )
        print(f" {horiz_line}")
        service_string = prompt_toolkit.prompt(
            "Please select a service by specifying the key: ",
            completer=srv_completer,
            complete_style=CompleteStyle.MULTI_COLUMN,
        )
        if service_string in tmtc_defs.defs:
            LOGGER.info(f"Selected service: {service_string}")
            return service_string
        else:
            LOGGER.warning("Invalid key, try again")


def build_service_word_completer(
    tmtc_defs: TmTcDefWrapper,
) -> WordCompleter:
    srv_list = []
    for service_entry in tmtc_defs.defs.items():
        srv_list.append(service_entry[0])
    srv_completer = WordCompleter(words=srv_list, ignore_case=True)
    return srv_completer


def prompt_op_code(tmtc_defs: TmTcDefWrapper, service: str) -> str:
    op_code_adjustment = 24
    info_adjustment = 56
    horz_line_num = op_code_adjustment + info_adjustment + 3
    horiz_line = horz_line_num * "-"
    op_code_info_str = "Operation Code".ljust(op_code_adjustment)
    info_string = "Information".ljust(info_adjustment)
    while True:
        print(f" {horiz_line}")
        print(f"|{op_code_info_str} | {info_string}|")
        print(f" {horiz_line}")
        if service in tmtc_defs.defs:
            op_code_entry = tmtc_defs.op_code_entry(service)
            op_code_entry.sort()
            completer = build_op_code_word_completer(
                service=service, op_code_entry=op_code_entry
            )
            for op_code in op_code_entry.op_code_dict.items():
                adjusted_op_code_entry = op_code[0].ljust(op_code_adjustment)
                adjusted_op_code_info = op_code[1][0].ljust(info_adjustment)
                print(f"|{adjusted_op_code_entry} | {adjusted_op_code_info}|")
            print(f" {horiz_line}")
            op_code_string = prompt_toolkit.prompt(
                "Please select an operation code by specifying the key: ",
                completer=completer,
                complete_style=CompleteStyle.MULTI_COLUMN,
            )
            if op_code_string in op_code_entry.op_code_dict.keys():
                LOGGER.info(f"Selected op code: {op_code_string}")
                return op_code_string
            else:
                LOGGER.warning("Invalid key, try again")
        else:
            LOGGER.warning(
                "Service not in dictionary. Setting default operation code 0"
            )
            return "0"


def build_op_code_word_completer(
    service: str, op_code_entry: OpCodeEntry
) -> WordCompleter:
    op_code_list = []
    for op_code_entry in op_code_entry.op_code_dict.items():
        op_code_list.append(op_code_entry[0])
    op_code_completer = WordCompleter(words=op_code_list, ignore_case=True)
    return op_code_completer
