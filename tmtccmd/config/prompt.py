import logging
import os
import re
from typing import Optional

import prompt_toolkit
from deprecated.sphinx import deprecated
from prompt_toolkit.completion import NestedCompleter, WordCompleter
from prompt_toolkit.history import History
from prompt_toolkit.shortcuts import CompleteStyle

from tmtccmd.config.tmtc import CmdTreeNode, OpCodeEntry, TmtcDefinitionWrapper

_LOGGER = logging.getLogger(__name__)


@deprecated(
    reason="use prompt_cmd_path instead",
    version="8.0.0",
)
def prompt_service(
    tmtc_defs: TmtcDefinitionWrapper,
    compl_style: CompleteStyle = CompleteStyle.READLINE_LIKE,
) -> str:
    service_adjustment = 20
    info_adjustment = 30
    horiz_line_num = service_adjustment + info_adjustment + 3
    horiz_line = horiz_line_num * "-"
    service_ladjusted = "Service".ljust(service_adjustment)
    info_string = "Information".ljust(info_adjustment)
    tmtc_defs.sort()
    while True:
        print(f" {horiz_line}")
        print(f"|{service_ladjusted} | {info_string}|")
        print(f" {horiz_line}")
        srv_completer = build_service_word_completer(tmtc_defs)
        for service_entry in tmtc_defs.defs.items():
            try:
                adjusted_service_entry = service_entry[0].ljust(service_adjustment)
                adjusted_service_info = service_entry[1][0].ljust(info_adjustment)
                print(f"|{adjusted_service_entry} | {adjusted_service_info}|")
            except AttributeError:
                _LOGGER.warning(
                    f"Error handling service entry {service_entry[0]}. Skipping.."
                )
        print(f" {horiz_line}")
        service_string = prompt_toolkit.prompt(
            "Please select a service by specifying the key: ",
            completer=srv_completer,
            complete_style=compl_style,
        )
        if service_string in tmtc_defs.defs:
            print(f"Selected service: {service_string}")
            return service_string
        else:
            _LOGGER.warning("Invalid key, try again")


def prompt_cmd_path(
    cmd_def_tree: CmdTreeNode,
    history: Optional[History] = None,
    compl_style: CompleteStyle = CompleteStyle.READLINE_LIKE,
) -> str:
    compl_dict = cmd_def_tree.name_dict
    compl_dict = compl_dict.get("/")
    if compl_dict is None:
        return "/"
    nested_completer = NestedCompleter.from_nested_dict(compl_dict, separator="/")
    help_txt = (
        f"Additional commands for prompt:{os.linesep}"
        f":p[b][f][<depth>] Tree Print | :r Retry | :h Help Text | :c Cancel {os.linesep}"
        f"Auto complete is available using Tab after typing the slash character.{os.linesep}"
        f"If a command history was passed, use arrow up to access it.{os.linesep}"
        f"You can also print a subtree by typing the path and appending :p[b][p][<depth>]."
        f"{os.linesep}The b option for printouts enables brief printouts without descriptions."
        f"{os.linesep}The p option for printouts overrides hide flags to display all hidden nodes."
        f"{os.linesep}"
    )
    print(help_txt)
    while True:
        path_or_cmd = prompt_toolkit.prompt(
            message="> ",
            history=history,
            completer=nested_completer,
            complete_style=compl_style,
        )
        if ":p" in path_or_cmd:
            list_of_patterns = path_or_cmd.split(":")
            tree_to_print = cmd_def_tree
            if cmd_def_tree.contains_path(list_of_patterns[0]):
                tree_to_print = cmd_def_tree.extract_subnode(list_of_patterns[0])
                # Should never happen.
                assert tree_to_print is not None
            with_descriptions = True
            depth = None
            show_hidden_elements = False
            pattern = r"p([a-zA-Z]*)(\d*)"
            matches = re.search(pattern, list_of_patterns[1])
            if matches:
                if "b" in matches.group(1):
                    with_descriptions = False
                if "f" in matches.group(1):
                    show_hidden_elements = True
                if matches.group(2).isdigit():
                    depth = int(matches.group(2))
            print(
                tree_to_print.str_for_tree(
                    with_description=with_descriptions,
                    max_depth=depth,
                    show_hidden_elements=show_hidden_elements,
                )
            )
            continue
        elif ":h" in path_or_cmd:
            print(help_txt)
            continue
        elif ":r" in path_or_cmd:
            continue
        elif ":c" in path_or_cmd:
            break
        if not cmd_def_tree.contains_path(f"/{path_or_cmd}"):
            yes_or_no = input(
                "Command definitions tree does not contain the path. Try again? [y/n]: "
            )
            if yes_or_no in ["y", "yes", "1"]:
                continue
        break
    return f"/{path_or_cmd}"


def build_service_word_completer(
    tmtc_defs: TmtcDefinitionWrapper,
) -> WordCompleter:
    srv_list = []
    for service_entry in tmtc_defs.defs.items():
        srv_list.append(service_entry[0])
    srv_completer = WordCompleter(words=srv_list, ignore_case=True)
    return srv_completer


def prompt_op_code(
    tmtc_defs: TmtcDefinitionWrapper,
    service: str,
    compl_style: CompleteStyle = CompleteStyle.READLINE_LIKE,
) -> str:
    op_code_adjustment = 24
    info_adjustment = 56
    horz_line_num = op_code_adjustment + info_adjustment + 3
    horiz_line = horz_line_num * "-"
    op_code_info_number_str = "Operation Code (Number)".ljust(op_code_adjustment)
    op_code_info_str_str = "Operation Code (Text)".ljust(op_code_adjustment)
    info_string = "Information".ljust(info_adjustment)
    if service in tmtc_defs.defs:
        op_code_entry = tmtc_defs.op_code_entry(service)
        completer = build_op_code_word_completer(op_code_entry=op_code_entry)
    else:
        _LOGGER.warning("Service not in dictionary. Setting default operation code 0")
        return "0"
    while True:

        def print_table(otype: str, dictionary: dict):
            print(f" {horiz_line}")
            print(f"|{otype} | {info_string}|")
            print(f" {horiz_line}")
            for op_code in dictionary.items():
                adjusted_op_code_entry = op_code[0].ljust(op_code_adjustment)
                adjusted_op_code_info = op_code[1][0].ljust(info_adjustment)
                print(f"|{adjusted_op_code_entry} | {adjusted_op_code_info}|")
            print(f" {horiz_line}")

        if len(op_code_entry.op_code_dict_str_keys) > 0:
            print_table(op_code_info_str_str, op_code_entry.op_code_dict_str_keys)
        if len(op_code_entry.op_code_dict_num_keys) > 0:
            print_table(op_code_info_number_str, op_code_entry.op_code_dict_num_keys)
        op_code_string = prompt_toolkit.prompt(
            "Please select an operation code by specifying the key: ",
            completer=completer,
            complete_style=compl_style,
        )
        if (
            op_code_string in op_code_entry.op_code_dict_str_keys.keys()
            or op_code_string in op_code_entry.op_code_dict_num_keys.keys()
        ):
            print(f"Selected op code: {op_code_string}")
            return op_code_string
        else:
            _LOGGER.warning("Invalid key, try again")


def build_op_code_word_completer(op_code_entry: OpCodeEntry) -> WordCompleter:
    op_code_list = []
    for op_code_str in op_code_entry.op_code_dict_num_keys.keys():
        op_code_list.append(op_code_str)
    for op_code_str in op_code_entry.op_code_dict_str_keys.keys():
        op_code_list.append(op_code_str)
    op_code_completer = WordCompleter(words=op_code_list, ignore_case=True)
    return op_code_completer
