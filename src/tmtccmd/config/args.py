"""
Argument parser modules for the TMTC commander core
"""
import argparse
import sys
from typing import Optional, List
from dataclasses import dataclass

from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.shortcuts import CompleteStyle
import prompt_toolkit

from tmtccmd.config.definitions import CoreModeList
from tmtccmd.config.tmtc_defs import TmTcDefWrapper, OpCodeEntry
from tmtccmd.config.cfg_hook import TmTcCfgHookBase
from tmtccmd.utility.conf_util import AnsiColors
from tmtccmd.logging import get_console_logger


LOGGER = get_console_logger()


def get_default_descript_txt() -> str:
    return (
        f"{AnsiColors.GREEN}TMTC Client Command Line Interface\n"
        f"{AnsiColors.RESET}This application provides generic components to execute "
        f"TMTC commanding\n"
    )


def create_default_args_parser(
    descript_txt: Optional[str] = None,
) -> argparse.ArgumentParser:
    if descript_txt is None:
        descript_txt = get_default_descript_txt()
    return argparse.ArgumentParser(
        description=descript_txt, formatter_class=argparse.RawTextHelpFormatter
    )


@dataclass
class ArgsGroup:
    service: str
    op_code: str
    mode: str
    listener: bool = False
    interactive: bool = False


class TmtccmdArgsWrapper:
    def __init__(self, descript_txt: Optional[str] = None):
        self.args_parser = create_default_args_parser(descript_txt)
        self.print_known_args = False
        self.print_unknown_args = False
        self.unknown_args = [""]
        self.args = ArgsGroup("", "", "")

    def add_default_tmtccmd_args(self):
        add_default_tmtccmd_args(self.args_parser)

    def parse(self, hook_obj: TmTcCfgHookBase):
        args, self.unknown_args = parse_default_tmtccmd_input_arguments(
            self.args_parser,
            hook_obj,
            print_known_args=self.print_known_args,
            print_unknown_args=self.print_unknown_args,
        )
        self.args.service = args.service
        self.args.op_code = args.op_code
        self.args.mode = args.mode
        self.args.listener = args.listener


def add_default_tmtccmd_args(parser: argparse.ArgumentParser):
    add_default_mode_arguments(parser)
    add_default_com_if_arguments(parser)
    add_generic_arguments(parser)
    add_cfdp_parser(parser)

    add_ethernet_arguments(parser)


def parse_default_tmtccmd_input_arguments(
    parser: argparse.ArgumentParser,
    hook_obj: TmTcCfgHookBase,
    print_known_args: bool = False,
    print_unknown_args: bool = False,
) -> (argparse.Namespace, List[str]):
    """Parses all input arguments
    :return: Input arguments contained in a special namespace and accessable by args.<variable>
    """

    if len(sys.argv) == 1:
        LOGGER.info(
            "No input arguments specified. Run with -h to get list of arguments"
        )

    args, unknown = parser.parse_known_args()

    if print_known_args:
        LOGGER.info("Printing known arguments:")
        for argument in vars(args):
            LOGGER.debug(argument + ": " + str(getattr(args, argument)))
    if print_unknown_args:
        LOGGER.info("Printing unknown arguments:")
        for argument in unknown:
            LOGGER.info(argument)

    args_post_processing(args, unknown, hook_obj.get_tmtc_definitions())
    return args, unknown


def add_cfdp_parser(arg_parser: argparse.ArgumentParser):
    subparsers = arg_parser.add_subparsers(
        title="CFDP",
        description="CCSDS File Delivery Protocol commands",
        help="CCDSDS File Delivery Commands",
        dest="cfdp",
    )
    cfdp = subparsers.add_parser("cfdp")
    cfdp.add_argument("-p", "--proxy")
    cfdp.add_argument(
        "-f", "--file", dest="cfdp_file", help="CFDP target file", default=None
    )
    cfdp.add_argument(
        "-d",
        "--dest",
        dest="cfdp_dest",
        help="CFDP file destination path",
        default=None,
    )


def add_generic_arguments(arg_parser: argparse.ArgumentParser):
    arg_parser.add_argument(
        "-s",
        "--service",
        help="Procedure service code which is passed to the TC handler objects",
        default=None,
    )
    arg_parser.add_argument(
        "-o",
        "--op_code",
        help="Procedcure operation code, which is passed to the TC packer functions",
        default=None,
    )
    arg_parser.add_argument(
        "-l",
        "--listener",
        help="The backend will be configured to go into listener mode after "
        "finishing the first queue",
        action="store_true",
        default=False,
    )
    arg_parser.add_argument(
        "-i",
        "--interactive",
        help="Enables interactive or multi-queue mode, where the backend will be confiogured "
        "to handle multiple queues",
        action="store_true",
        default=False,
    )
    arg_parser.add_argument(
        "-t",
        "--tm_timeout",
        type=float,
        help="Default inter-packet delay" " Default: 3 seconds",
        default=3.0,
    )


def add_default_mode_arguments(arg_parser: argparse.ArgumentParser):
    from tmtccmd.config.definitions import CoreModeList, CoreModeStrings

    help_text = f"Core Modes. Default: {CoreModeStrings[CoreModeList.ONE_QUEUE_MODE]}\n"
    one_q = (
        f"{CoreModeList.ONE_QUEUE_MODE} or "
        f"{CoreModeStrings[CoreModeList.ONE_QUEUE_MODE]}: "
        f"One Queue Command Mode\n"
    )
    listener_help = (
        f"{CoreModeList.LISTENER_MODE} or {CoreModeStrings[CoreModeList.LISTENER_MODE]}: "
        f"Listener Mode\n"
    )
    multi_q = (
        f"{CoreModeList.MULTI_INTERACTIVE_QUEUE_MODE} or "
        f"{CoreModeStrings[CoreModeList.MULTI_INTERACTIVE_QUEUE_MODE]}: "
        f"Multi Queue and Interactive Command Mode\n"
    )
    gui_help = (
        f"{CoreModeList.GUI_MODE} or "
        f"{CoreModeStrings[CoreModeList.GUI_MODE]}: "
        f"GUI mode\n"
    )
    help_text += one_q + listener_help + gui_help
    arg_parser.add_argument(
        "-m",
        "--mode",
        type=str,
        help=help_text,
        default=CoreModeStrings[CoreModeList.ONE_QUEUE_MODE],
    )


def add_default_com_if_arguments(arg_parser: argparse.ArgumentParser):
    from tmtccmd.config.definitions import CoreComInterfacesDict, CoreComInterfaces

    help_text = (
        "Core Communication Interface. If this is not specified, the commander core\n"
        "will try to extract it from the JSON or prompt it from the user.\n"
    )
    dummy_line = (
        f"{CoreComInterfacesDict[CoreComInterfaces.DUMMY.value]}: Dummy Interface\n"
    )
    udp_line = (
        f"{CoreComInterfacesDict[CoreComInterfaces.TCPIP_UDP.value]}: " f"UDP client\n"
    )
    ser_dle_line = (
        f"{CoreComInterfacesDict[CoreComInterfaces.SERIAL_DLE.value]}: "
        f"Serial with DLE transport layer\n"
    )
    ser_fixed_line = (
        f"{CoreComInterfacesDict[CoreComInterfaces.SERIAL_FIXED_FRAME.value]}: "
        f"Serial with fixed frames\n"
    )
    ser_qemu_line = (
        f"{CoreComInterfacesDict[CoreComInterfaces.SERIAL_QEMU.value]}: "
        f"QEMU serial interface\n"
    )
    help_text += dummy_line + ser_dle_line + udp_line + ser_fixed_line + ser_qemu_line
    arg_parser.add_argument(
        "-c",
        "--com_if",
        type=str,
        help=help_text,
        default=CoreComInterfaces.UNSPECIFIED.value,
    )


def add_ethernet_arguments(arg_parser: argparse.ArgumentParser):
    arg_parser.add_argument("--h-ip", help="Host (Computer) IP. Default:''", default="")
    arg_parser.add_argument(
        "--t-ip", help="Target IP. Default: Localhost 127.0.0.1", default="127.0.0.1"
    )


def args_post_processing(
    args, unknown: list, service_op_code_dict: TmTcDefWrapper
) -> None:
    """Handles the parsed arguments.
    :param service_op_code_dict:
    :param args: Namespace objects
        (see https://docs.python.org/dev/library/argparse.html#argparse.Namespace)
    :param unknown: List of unknown parameters.
    :return: None
    """
    if len(unknown) > 0:
        print("Unknown arguments detected: " + str(unknown))
    if len(sys.argv) > 1:
        handle_unspecified_args(args, service_op_code_dict)
    if len(sys.argv) == 1:
        handle_empty_args(args, service_op_code_dict)


def handle_unspecified_args(args, tmtc_defs: TmTcDefWrapper) -> None:
    """If some arguments are unspecified, they are set here with (variable) default values.
    :param args: Arguments from calling parse method
    :param tmtc_defs:
    :return: None
    """
    from tmtccmd.config.definitions import CoreModeStrings

    if args.mode is None:
        args.mode = CoreModeStrings[CoreModeList.ONE_QUEUE_MODE]
    if tmtc_defs is None:
        LOGGER.warning("Invalid Service to Op-Code dictionary detected")
        if args.service is None:
            args.service = "0"
        if args.op_code is None:
            args.op_code = "0"
        return
    if args.service is None:
        if args.mode == CoreModeStrings[CoreModeList.ONE_QUEUE_MODE]:
            LOGGER.info("No service argument (-s) specified, prompting from user..")
            # Try to get the service list from the hook base and prompt service from user
            args.service = prompt_service(tmtc_defs)
    if args.op_code is None:
        current_service = args.service
        args.op_code = prompt_op_code(tmtc_defs, current_service)
    if args.tm_timeout is None:
        args.tm_timeout = 5.0
    if args.listener is None:
        args.listener = False


def handle_empty_args(args, service_op_code_dict: TmTcDefWrapper) -> None:
    """If no args were supplied, request input from user directly.
    :param service_op_code_dict:
    :param args:
    :return:
    """
    LOGGER.info("No arguments specified..")
    handle_unspecified_args(args, service_op_code_dict)


def prompt_service(tmtc_defs: TmTcDefWrapper) -> str:
    service_adjustment = 20
    info_adjustment = 30
    horiz_line_num = service_adjustment + info_adjustment + 3
    horiz_line = horiz_line_num * "-"
    service_string = "Service".ljust(service_adjustment)
    info_string = "Information".ljust(info_adjustment)
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
        if service_string in tmtc_defs:
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
            completer = build_op_code_word_completer(
                service=service, op_code_entry=op_code_entry
            )
            for op_code_entry in op_code_entry.op_code_dict.items():
                adjusted_op_code_entry = op_code_entry[0].ljust(op_code_adjustment)
                adjusted_op_code_info = op_code_entry[1][0].ljust(info_adjustment)
                print(f"|{adjusted_op_code_entry} | {adjusted_op_code_info}|")
            print(f" {horiz_line}")
            op_code_string = prompt_toolkit.prompt(
                "Please select an operation code by specifying the key: ",
                completer=completer,
                complete_style=CompleteStyle.MULTI_COLUMN,
            )
            if op_code_string in op_code_entry:
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
