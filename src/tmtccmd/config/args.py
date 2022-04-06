"""
Argument parser modules for the TMTC commander core
"""
import argparse
import pprint
import sys
from typing import Optional

from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.shortcuts import CompleteStyle
import prompt_toolkit

from tmtccmd.config.definitions import (
    CoreModeList,
    ServiceOpCodeDictT,
    OpCodeEntryT,
    OpCodeDictKeys,
)
from tmtccmd.config.hook import TmTcHookBase
from tmtccmd.utility.conf_util import AnsiColors
from tmtccmd.logging import get_console_logger


LOGGER = get_console_logger()


def get_default_descript_txt() -> str:
    return (
        f"{AnsiColors.GREEN}TMTC Client Command Line Interface\n"
        f"{AnsiColors.RESET}This application provides generic components to execute "
        f"TMTC commanding.\n"
        f"The developer is expected to specify the packaged telecommands for a given\n"
        "service and operation code combination. The developer is also expected\n"
        "to implement the handling of telemetry. All these tasks can be done by implementing\n"
        "a hook object and passing it to the core."
    )


def create_default_args_parser(
    descript_txt: Optional[str] = None,
) -> argparse.ArgumentParser:
    if descript_txt is None:
        descript_txt = get_default_descript_txt()
    return argparse.ArgumentParser(
        description=descript_txt, formatter_class=argparse.RawTextHelpFormatter
    )


def add_default_tmtccmd_args(parser: argparse.ArgumentParser):
    add_default_mode_arguments(parser)
    add_default_com_if_arguments(parser)
    add_generic_arguments(parser)

    add_ethernet_arguments(parser)

    parser.add_argument(
        "--tctf",
        type=float,
        help="TC Timeout Factor. Multiplied with "
        "TM Timeout, TC sent again after this time period. Default: 3.5",
        default=3.5,
    )
    parser.add_argument(
        "-r",
        "--raw-print",
        help="Supply -r to print all raw TM data directly",
        action="store_true",
    )
    parser.add_argument(
        "-d",
        "--sh-display",
        help="Supply -d to print short output",
        action="store_true",
    )
    parser.add_argument(
        "-k",
        "--hk",
        dest="print_hk",
        help="Supply -k or --hk to print HK data",
        action="store_true",
    )
    parser.add_argument(
        "--rs",
        dest="resend_tc",
        help="Specify whether TCs are sent again after timeout",
        action="store_true",
    )


def parse_default_input_arguments(
    parser: argparse.ArgumentParser,
    hook_obj: TmTcHookBase,
    print_known_args: bool = False,
    print_unknown_args: bool = False,
) -> argparse.Namespace:
    """Parses all input arguments
    :return: Input arguments contained in a special namespace and accessable by args.<variable>
    """
    from tmtccmd.utility.conf_util import AnsiColors

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

    args_post_processing(args, unknown, hook_obj.get_service_op_code_dictionary())
    return args


def add_generic_arguments(arg_parser: argparse.ArgumentParser):
    arg_parser.add_argument(
        "-s", "--service", type=str, help="Service to test", default=None
    )
    arg_parser.add_argument(
        "-o",
        "--op_code",
        help="Operation code, which is passed to the TC packer functions",
        default=None,
    )
    arg_parser.add_argument(
        "-l",
        "--listener",
        help="Determine whether the listener mode will be active after performing the operation",
        action="store_true",
        default=None,
    )
    arg_parser.add_argument(
        "-t",
        "--tm_timeout",
        type=float,
        help="TM Timeout when listening to verification sequence."
        " Default: 5 seconds",
        default=None,
    )
    arg_parser.add_argument(
        "--nl",
        dest="print_log",
        help="Supply --nl to suppress print output to log files.",
        action="store_false",
    )
    arg_parser.add_argument(
        "--np",
        dest="print_tm",
        help="Supply --np to suppress print output to console.",
        action="store_false",
    )


def add_default_mode_arguments(arg_parser: argparse.ArgumentParser):
    from tmtccmd.config.definitions import CoreModeList, CoreModeStrings

    help_text = "Core Modes. Default: seqcmd\n"
    seq_help = (
        f"{CoreModeList.SEQUENTIAL_CMD_MODE} or "
        f"{CoreModeStrings[CoreModeList.SEQUENTIAL_CMD_MODE]}: "
        f"Sequential Command Mode\n"
    )
    listener_help = (
        f"{CoreModeList.LISTENER_MODE} or {CoreModeStrings[CoreModeList.LISTENER_MODE]}: "
        f"Listener Mode\n"
    )
    gui_help = (
        f"{CoreModeList.GUI_MODE} or "
        f"{CoreModeStrings[CoreModeList.GUI_MODE]}: "
        f"GUI mode\n"
    )
    help_text += seq_help + listener_help + gui_help
    arg_parser.add_argument(
        "-m",
        "--mode",
        type=str,
        help=help_text,
        default=CoreModeStrings[CoreModeList.SEQUENTIAL_CMD_MODE],
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
    arg_parser.add_argument(
        "--client-ip", help="Client(Computer) IP. Default:''", default=""
    )
    arg_parser.add_argument(
        "--board-ip", help="Board IP. Default: Localhost 127.0.0.1", default="127.0.0.1"
    )


def args_post_processing(
    args, unknown: list, service_op_code_dict: ServiceOpCodeDictT
) -> None:
    """Handles the parsed arguments.
    :param args: Namespace objects (see https://docs.python.org/dev/library/argparse.html#argparse.Namespace)
    :param unknown: List of unknown parameters.
    :return: None
    """
    if len(unknown) > 0:
        print("Unknown arguments detected: " + str(unknown))
    if len(sys.argv) > 1:
        handle_unspecified_args(args, service_op_code_dict)
    if len(sys.argv) == 1:
        handle_empty_args(args, service_op_code_dict)


def handle_unspecified_args(args, service_op_code_dict: ServiceOpCodeDictT) -> None:
    """If some arguments are unspecified, they are set here with (variable) default values.
    :param args:
    :return: None
    """
    from tmtccmd.config.definitions import CoreModeStrings

    if args.mode is None:
        args.mode = CoreModeStrings[CoreModeList.SEQUENTIAL_CMD_MODE]
    if service_op_code_dict is None:
        LOGGER.warning("Invalid Service to Op-Code dictionary detected")
        if args.service is None:
            args.service = "0"
        if args.op_code is None:
            args.op_code = "0"
        return
    if args.service is None:
        if args.mode == CoreModeStrings[CoreModeList.SEQUENTIAL_CMD_MODE]:
            LOGGER.info("No service argument (-s) specified, prompting from user..")
            # Try to get the service list from the hook base and prompt service from user
            args.service = prompt_service(service_op_code_dict)
    if args.op_code is None:
        current_service = args.service
        args.op_code = prompt_op_code(
            service_op_code_dict=service_op_code_dict, service=current_service
        )
    op_code_value = service_op_code_dict.get(args.service)
    if op_code_value is None:
        LOGGER.warning(f"No Service to Op-Code entry found for service {args.service}")
    else:
        op_code_value = service_op_code_dict[args.service][1]
        op_code_options = op_code_value[args.op_code][1]
        if op_code_options is not None and isinstance(op_code_options, dict):
            if op_code_options.get(OpCodeDictKeys.ENTER_LISTENER_MODE):
                if args.listener is None:
                    LOGGER.info(
                        "Detected op code configuration: Enter listener mode after command"
                    )
                    args.listener = True
                else:
                    LOGGER.warning(
                        "Detected op code listerner mode configuration but is "
                        "overriden by CLI argument"
                    )
        if op_code_options is not None:
            timeout = op_code_options.get(OpCodeDictKeys.TIMEOUT)
            if timeout is not None:
                if args.tm_timeout is None:
                    LOGGER.info(
                        f"Detected op code configuration: Set custom timeout {timeout}"
                    )
                    args.tm_timeout = timeout
                else:
                    LOGGER.warning(
                        "Detected op code timeout configuration but is overriden by CLI argument"
                    )
    if args.tm_timeout is None:
        args.tm_timeout = 5.0
    if args.listener is None:
        args.listener = False


def handle_empty_args(args, service_op_code_dict: ServiceOpCodeDictT) -> None:
    """If no args were supplied, request input from user directly.
    :param args:
    :return:
    """
    LOGGER.info("No arguments specified..")
    handle_unspecified_args(args, service_op_code_dict)


def prompt_service(service_op_code_dict: ServiceOpCodeDictT) -> str:
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
        srv_completer = build_service_word_completer(
            service_op_code_dict=service_op_code_dict
        )
        for service_entry in service_op_code_dict.items():
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
        if service_string in service_op_code_dict:
            LOGGER.info(f"Selected service: {service_string}")
            return service_string
        else:
            LOGGER.warning("Invalid key, try again")


def build_service_word_completer(
    service_op_code_dict: ServiceOpCodeDictT,
) -> WordCompleter:
    srv_list = []
    for service_entry in service_op_code_dict.items():
        srv_list.append(service_entry[0])
    srv_completer = WordCompleter(words=srv_list, ignore_case=True)
    return srv_completer


def prompt_op_code(service_op_code_dict: ServiceOpCodeDictT, service: str) -> str:
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
        if service in service_op_code_dict:
            op_code_dict = service_op_code_dict[service][1]
            completer = build_op_code_word_completer(
                service=service, op_code_dict=op_code_dict
            )
            for op_code_entry in op_code_dict.items():
                adjusted_op_code_entry = op_code_entry[0].ljust(op_code_adjustment)
                adjusted_op_code_info = op_code_entry[1][0].ljust(info_adjustment)
                print(f"|{adjusted_op_code_entry} | {adjusted_op_code_info}|")
            print(f" {horiz_line}")
            op_code_string = prompt_toolkit.prompt(
                "Please select an operation code by specifying the key: ",
                completer=completer,
                complete_style=CompleteStyle.MULTI_COLUMN,
            )
            if op_code_string in op_code_dict:
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
    service: str, op_code_dict: OpCodeEntryT
) -> WordCompleter:
    op_code_list = []
    for op_code_entry in op_code_dict.items():
        op_code_list.append(op_code_entry[0])
    op_code_completer = WordCompleter(words=op_code_list, ignore_case=True)
    return op_code_completer
