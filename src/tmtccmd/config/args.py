"""
Argument parser modules for the TMTC commander core
"""
import argparse
import sys

from tmtccmd.config.definitions import CoreModeList, ServiceOpCodeDictT
from tmtccmd.utility.logger import get_console_logger


LOGGER = get_console_logger()


def parse_input_arguments(
        print_known_args: bool = False, print_unknown_args: bool = False
) -> argparse.Namespace:
    try:
        from tmtccmd.config.hook import get_global_hook_obj
        hook_obj = get_global_hook_obj()
        args = hook_obj.custom_args_parsing()
        if args is None:
            return parse_default_input_arguments(print_known_args, print_unknown_args)
    except ImportError:
        return parse_default_input_arguments(print_known_args, print_unknown_args)


def parse_default_input_arguments(print_known_args: bool = False, print_unknown_args: bool = False):
    """Parses all input arguments
    :return: Input arguments contained in a special namespace and accessable by args.<variable>
    """
    from tmtccmd.utility.conf_util import AnsiColors
    descrip_text = \
        f"{AnsiColors.GREEN}TMTC Client Command Line Interface\n" \
        f"{AnsiColors.RESET}This application provides generic components to execute " \
        f"TMTC commanding.\n" \
        f"The developer is expected to specify the packaged telecommands for a given\n" \
        "service and operation code combination. The developer is also expected\n" \
        "to implement the handling of telemetry. All these tasks can be done by implementing\n" \
        "a hook object and passing it to the core."
    arg_parser = argparse.ArgumentParser(
        description=descrip_text,
        formatter_class=argparse.RawTextHelpFormatter
    )

    add_default_mode_arguments(arg_parser)
    add_default_com_if_arguments(arg_parser)
    add_generic_arguments(arg_parser)

    # TODO: Only add this if TMTC commander is configured for Ethernet?
    add_ethernet_arguments(arg_parser)

    arg_parser.add_argument(
        '--tc_timeout_factor', type=float, help='TC Timeout Factor. Multiplied with '
        'TM Timeout, TC sent again after this time period. Default: 3.5', default=3.5
    )
    arg_parser.add_argument(
        '-r', '--raw_data_print', help='Supply -r to print all raw TM data directly',
        action='store_true'
    )
    arg_parser.add_argument(
        '-d', '--short_display_mode', help='Supply -d to print short output', action='store_true'
    )
    arg_parser.add_argument(
        '--hk', dest='print_hk', help='Supply -k or --hk to print HK data', action='store_true'
    )
    arg_parser.add_argument(
        '--rs', dest="resend_tc", help='Specify whether TCs are sent again after timeout',
        action='store_true'
    )

    if len(sys.argv) == 1:
        LOGGER.info("No input arguments specified. Run with -h to get list of arguments")

    args, unknown = arg_parser.parse_known_args()

    if print_known_args:
        LOGGER.info("Printing known arguments:")
        for argument in vars(args):
            LOGGER.debug(argument + ": " + str(getattr(args, argument)))
    if print_unknown_args:
        LOGGER.info("Printing unknown arguments:")
        for argument in unknown:
            LOGGER.info(argument)

    args_post_processing(args, unknown)
    return args


def add_generic_arguments(arg_parser: argparse.ArgumentParser):
    arg_parser.add_argument('-s', '--service', type=str, help='Service to test', default=None)
    arg_parser.add_argument(
        '-o', '--op_code', help='Operation code, which is passed to the TC packer functions',
        default=None
    )
    arg_parser.add_argument(
        '-l', '--listener',
        help='Determine whether the listener mode will be active after performing the operation',
        action='store_false'
    )
    arg_parser.add_argument(
        '-t', '--tm_timeout', type=float, help='TM Timeout when listening to verification sequence.'
        ' Default: 5 seconds', default=5.0
    )
    arg_parser.add_argument(
        '--nl', dest='print_log', help='Supply --nl to suppress print output to log files.',
        action='store_false'
    )
    arg_parser.add_argument(
        '--np', dest='print_tm', help='Supply --np to suppress print output to console.',
        action='store_false'
    )


def add_default_mode_arguments(arg_parser: argparse.ArgumentParser):
    from tmtccmd.config.definitions import CoreModeList, CoreModeStrings
    help_text = 'Core Modes. Default: seqcmd\n'
    seq_help = \
        f"{CoreModeList.SEQUENTIAL_CMD_MODE} or " \
        f"{CoreModeStrings[CoreModeList.SEQUENTIAL_CMD_MODE]}: " \
        f"Sequential Command Mode\n"
    listener_help = \
        f"{CoreModeList.LISTENER_MODE} or {CoreModeStrings[CoreModeList.LISTENER_MODE]}: " \
        f"Listener Mode\n"
    gui_help = \
        f"{CoreModeList.GUI_MODE} or " \
        f"{CoreModeStrings[CoreModeList.GUI_MODE]}: " \
        f"GUI mode\n"
    help_text += seq_help + listener_help + gui_help
    arg_parser.add_argument(
        '-m', '--mode', type=str, help=help_text, default="seqcmd"
    )


def add_default_com_if_arguments(arg_parser: argparse.ArgumentParser):
    from tmtccmd.config.definitions import CoreComInterfacesDict, CoreComInterfaces
    help_text = "Core Communication Interface. If this is not specified, the commander core\n" \
                "will try to extract it from the JSON or prompt it from the user.\n"
    dummy_line = \
        f"{CoreComInterfacesDict[CoreComInterfaces.DUMMY.value]}: Dummy Interface\n"
    udp_line = \
        f"{CoreComInterfacesDict[CoreComInterfaces.TCPIP_UDP.value]}: " \
        f"UDP client\n"
    ser_dle_line = \
        f"{CoreComInterfacesDict[CoreComInterfaces.SERIAL_DLE.value]}: " \
        f"Serial with DLE transport layer\n"
    ser_fixed_line = \
        f"{CoreComInterfacesDict[CoreComInterfaces.SERIAL_FIXED_FRAME.value]}: " \
        f"Serial with fixed frames\n"
    ser_qemu_line = \
        f"{CoreComInterfacesDict[CoreComInterfaces.SERIAL_QEMU.value]}: " \
        f"QEMU serial interface\n"
    help_text += dummy_line + ser_dle_line + udp_line + ser_fixed_line + ser_qemu_line
    arg_parser.add_argument(
        '-c', '--com_if', type=str, help=help_text, default=CoreComInterfaces.UNSPECIFIED.value
    )


def add_ethernet_arguments(arg_parser: argparse.ArgumentParser):
    arg_parser.add_argument('--clientIP', help='Client(Computer) IP. Default:\'\'', default='')
    arg_parser.add_argument(
        '--boardIP', help='Board IP. Default: Localhost 127.0.0.1', default="127.0.0.1")


def args_post_processing(args, unknown: list) -> None:
    """Handles the parsed arguments.
    :param args: Namespace objects (see https://docs.python.org/dev/library/argparse.html#argparse.Namespace)
    :param unknown: List of unknown parameters.
    :return: None
    """
    if len(unknown) > 0:
        print("Unknown arguments detected: " + str(unknown))
    if len(sys.argv) > 1:
        handle_unspecified_args(args)
    if len(sys.argv) == 1:
        handle_empty_args(args)


def handle_unspecified_args(args) -> None:
    """If some arguments are unspecified, they are set here with (variable) default values.
    :param args:
    :return: None
    """
    from tmtccmd.config.hook import get_global_hook_obj
    if args.tm_timeout is None:
        args.tm_timeout = 5.0
    if args.mode is None:
        args.mode = CoreModeList.SEQUENTIAL_CMD_MODE
    service_op_code_dict = dict()
    if args.service is None or args.op_code is None:
        hook_obj = get_global_hook_obj()
        service_op_code_dict = hook_obj.get_service_op_code_dictionary()
    if args.service is None:
        LOGGER.info("No service argument (-s) specified, prompting from user..")
        # Try to get the service list from the hook base and prompt service from user
        args.service = prompt_service(service_op_code_dict)
        if args.op_code is None:
            current_service = args.service
            args.op_code = prompt_op_code(service_op_code_dict=service_op_code_dict, service=current_service)
    elif args.op_code is None:
        current_service = args.service
        args.op_code = prompt_op_code(service_op_code_dict=service_op_code_dict, service=current_service)


def handle_empty_args(args) -> None:
    """If no args were supplied, request input from user directly.
    :param args:
    :return:
    """
    LOGGER.info("No arguments specified..")
    handle_unspecified_args(args=args)


def prompt_service(service_op_code_dict: ServiceOpCodeDictT) -> str:
    service_adjustment = 10
    info_adjustment = 30
    horiz_line_num = service_adjustment + info_adjustment + 3
    horiz_line = horiz_line_num * "-"
    service_string = "Service".ljust(service_adjustment)
    info_string = "Information".ljust(info_adjustment)
    while True:
        LOGGER.info(f"{service_string} | {info_string}")
        LOGGER.info(horiz_line)
        for service_entry in service_op_code_dict.items():
            adjusted_service_entry = service_entry[0].ljust(service_adjustment)
            adjusted_service_info = service_entry[1][0].ljust(info_adjustment)
            LOGGER.info(f"{adjusted_service_entry} | {adjusted_service_info}")
        service_string = input("Please select a service by specifying the key: ")
        if service_string in service_op_code_dict:
            LOGGER.info(f"Selected service: {service_string}")
            return service_string
        else:
            LOGGER.warning("Invalid key, try again")


def prompt_op_code(service_op_code_dict: ServiceOpCodeDictT, service: str) -> str:
    op_code_adjustment = 16
    info_adjustment = 34
    horz_line_num = op_code_adjustment + info_adjustment + 3
    horiz_line = horz_line_num * "-"
    op_code_string = "Operation Code".ljust(op_code_adjustment)
    info_string = "Information".ljust(info_adjustment)
    while True:
        LOGGER.info(f"{op_code_string} | {info_string}")
        LOGGER.info(horiz_line)
        if service in service_op_code_dict:
            op_code_dict = service_op_code_dict[service][1]
            for op_code_entry in op_code_dict.items():
                adjusted_op_code_entry = op_code_entry[0].ljust(op_code_adjustment)
                adjusted_op_code_info = op_code_entry[1][0].ljust(info_adjustment)
                LOGGER.info(f"{adjusted_op_code_entry} | {adjusted_op_code_info}")
            op_code_string = input("Please select an operation code by specifying the key: ")
            if op_code_string in op_code_dict:
                LOGGER.info(f"Selected op code: {op_code_string}")
                return op_code_string
            else:
                LOGGER.warning("Invalid key, try again")
        else:
            LOGGER.warning("Service not in dictionary. Setting default operation code 0")
            return "0"
