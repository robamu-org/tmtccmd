#!/usr/bin/python3.8
"""
Argument parser module.
"""
import argparse
import sys
from tmtccmd.utility.tmtcc_logger import get_logger


LOGGER = get_logger()


def parse_input_arguments(
        print_known_args: bool = False, print_unknown_args: bool = False
) -> argparse.Namespace:
    try:
        from tmtccmd.core.hook_helper import get_global_hook_obj
        hook_obj = get_global_hook_obj()
        args = hook_obj.custom_args_parsing()
        if args is None:
            return parse_default_input_arguments(print_known_args, print_unknown_args)
    except ImportError:
        return parse_default_input_arguments(print_known_args, print_unknown_args)


def parse_default_input_arguments(print_known_args: bool = False, print_unknown_args: bool = False):
    """
    Parses all input arguments
    :return: Input arguments contained in a special namespace and accessable by args.<variable>
    """
    arg_parser = argparse.ArgumentParser(description="TMTC Client Command Line Interface")

    add_default_mode_arguments(arg_parser)
    add_default_com_if_arguments(arg_parser)
    add_generic_arguments(arg_parser)

    # TODO: Only add this if TMTC commander is configured for Ethernet?
    add_ethernet_arguments(arg_parser)

    arg_parser.add_argument(
        '--tc_timeout_factor', type=float, help='TC Timeout Factor. Multiplied with '
        'TM Timeout, TC sent again after this time period. Default: 3.5', default=3.5)
    arg_parser.add_argument(
        '-r', '--raw_data_print', help='Supply -r to print all raw TM data directly',
        action='store_true')
    arg_parser.add_argument(
        '-d', '--short_display_mode', help='Supply -d to print short output', action='store_true')
    arg_parser.add_argument(
        '--hk', dest='print_hk', help='Supply -k or --hk to print HK data', action='store_true')
    arg_parser.add_argument(
        '--rs', dest="resend_tc", help='Specify whether TCs are sent again after timeout',
        action='store_true')

    if len(sys.argv) == 1:
        print("No Input Arguments specified.")
        arg_parser.print_help()

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
    arg_parser.add_argument(
        '-o', '--op_code', help='Operation code, which is passed to the TC '
                                'packer functions', default=0)
    arg_parser.add_argument('-s', '--service', help='Service to test. Default: 17', default=17)
    arg_parser.add_argument(
        '-l', '--listener',  help='Determine whether the listener mode will be active '
                                  'after performing the operation',
        action='store_false')
    arg_parser.add_argument(
        '-t', '--tm_timeout', type=float, help='TM Timeout when listening to verification sequence.'
        ' Default: 5 seconds', default=5.0)
    arg_parser.add_argument(
        '--nl', dest='print_log', help='Supply --nl to suppress print output to log files.',
        action='store_false')
    arg_parser.add_argument(
        '--np', dest='print_tm', help='Supply --np to suppress print output to console.',
        action='store_false')


def add_default_mode_arguments(arg_parser: argparse.ArgumentParser):
    arg_parser.add_argument(
        '-m', '--mode', type=int, help='Target Mode. Default is 1 (Listener Mode), '
        '1: Listener Mode, 2: Single Command Mode, 3: Service Test Mode, '
        '4: Software Test Mode', default=0)


def add_default_com_if_arguments(arg_parser: argparse.ArgumentParser):
    arg_parser.add_argument(
        '-c', '--com_if', type=int, help='Communication Interface. 0: Dummy Interface, 1: Serial,'
                                         '2: UDP', default=2)


def add_ethernet_arguments(arg_parser: argparse.ArgumentParser):
    arg_parser.add_argument('--clientIP', help='Client(Computer) IP. Default:\'\'', default='')
    arg_parser.add_argument(
        '--boardIP', help='Board IP. Default: Localhost 127.0.0.1', default="127.0.0.1")


def args_post_processing(args, unknown: list) -> None:
    """
    Handles the parsed arguments.
    :param args: Namespace objects
    (see https://docs.python.org/dev/library/argparse.html#argparse.Namespace)
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
    """
    If some arguments are unspecified, they are set here with (variable) default values.
    :param args:
    :return: None
    """
    if args.com_if == 1 and args.tm_timeout is None:
        args.tm_timeout = 6.0
    if args.mode is None:
        print("No mode specified with -m Parameter.")
        print("Possible Modes: ")
        print("1: Listener Mode")
        print("2: Single Command Mode with manual command")
        print("3: Service Mode, Commands specified in pus_tc folder")
        print("4: Software Mode, runs all command specified in tmtcc_pus_tc_packer.py")
        print("5: Unit Test, runs unit test specified in obsw_module_test.py")
        args.mode = input("Please enter Mode: ")
        if args.mode == 1 and args.service is None:
            args.service = input("No Service specified for Service Mode. "
                                 "Please enter PUS G_SERVICE number: ")


def handle_empty_args(args) -> None:
    """
    If no args were supplied, request input from user directly.
    TODO: This still needs to be extended.
    :param args:
    :return:
    """
    print_hk = input("Print HK packets ? (y/n or yes/no)")
    try:
        print_hk = print_hk.lower()
    except TypeError:
        pass
    if print_hk in ('y', 'yes', 1):
        args.print_hk = True
    else:
        args.print_hk = False
    print_to_log = input("Export G_SERVICE test output to log files ? (y/n or yes/no)")
    try:
        print_to_log = print_to_log.lower()
    except TypeError:
        pass
    if print_to_log in ('n', 'no', 0):
        args.printFile = False
    else:
        args.printFile = True