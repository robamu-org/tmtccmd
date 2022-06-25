"""
Argument parser modules for the TMTC commander core
"""
import argparse
import sys
from typing import Optional, List
from dataclasses import dataclass

from tmtccmd.config.definitions import CoreModeList
from tmtccmd.config.prompt import prompt_service, prompt_op_code
from tmtccmd.config.tmtc_defs import TmTcDefWrapper
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
    service: Optional[str] = None
    op_code: Optional[str] = None
    mode: str = ""
    com_if: str = ""
    delay: float = 0.0
    listener: bool = False
    interactive: bool = False


class ArgParserWrapper:
    def __init__(
        self,
        parser: Optional[argparse.ArgumentParser] = None,
        descript_txt: Optional[str] = None,
    ):
        if parser is None:
            self.args_parser = create_default_args_parser(descript_txt)
            add_default_tmtccmd_args(self.args_parser)
        else:
            self.args_parser = parser
        self.print_known_args = False
        self.print_unknown_args = False
        self.unknown_args = [""]
        self.args_converted: Optional[ArgsGroup] = None
        self.args_raw = None

    def add_default_tmtccmd_args(self):
        add_default_tmtccmd_args(self.args_parser)

    def parse(self, hook_obj: TmTcCfgHookBase, use_prompts: bool):
        self.args_raw, self.unknown_args = parse_default_tmtccmd_input_arguments(
            self.args_parser,
            print_known_args=self.print_known_args,
            print_unknown_args=self.print_unknown_args,
        )
        self.args_converted = process_tmtccmd_args(
            self.args_raw, hook_obj.get_tmtc_definitions(), use_prompts
        )

    @property
    def delay(self):
        return self.args_converted.delay

    @property
    def service(self):
        return self.args_converted.service

    @property
    def op_code(self):
        return self.args_converted.op_code

    @property
    def mode(self):
        return self.args_converted.mode

    @property
    def com_if(self):
        return self.args_converted.com_if


def add_default_tmtccmd_args(parser: argparse.ArgumentParser):
    add_default_mode_arguments(parser)
    add_default_com_if_arguments(parser)
    add_generic_arguments(parser)
    add_cfdp_parser(parser)

    add_ethernet_arguments(parser)


def process_tmtccmd_args(
    args: argparse.Namespace, tmtc_defs: TmTcDefWrapper, use_prompts: bool
) -> ArgsGroup:
    """If some arguments are unspecified, they are set here with (variable) default values.
    :param args: Arguments from calling parse method
    :param tmtc_defs:
    :param use_prompts: Specify whether terminal prompts are allowed to retrieve unspecified
        arguments. For something like a GUI, it might make sense to disable this
    :return: None
    """
    from tmtccmd.config.definitions import CoreModeStrings

    group = ArgsGroup()
    if args.mode is None:
        group.mode = CoreModeStrings[CoreModeList.ONE_QUEUE_MODE]
    else:
        group.mode = args.mode
    if tmtc_defs is None:
        LOGGER.warning("Invalid Service to Op-Code dictionary detected")
        if args.service is None:
            group.service = "0"
        if args.op_code is None:
            group.op_code = "0"
    else:
        if args.service is None:
            if args.mode == CoreModeStrings[CoreModeList.ONE_QUEUE_MODE]:
                if use_prompts:
                    LOGGER.info(
                        "No service argument (-s) specified, prompting from user.."
                    )
                    # Try to get the service list from the hook base and prompt service from user
                    group.service = prompt_service(tmtc_defs)
        else:
            group.service = args.service
        if args.op_code is None:
            current_service = group.service
            if use_prompts:
                group.op_code = prompt_op_code(tmtc_defs, current_service)
        else:
            group.op_code = args.op_code
    if args.delay is None:
        if group.mode == CoreModeStrings[CoreModeList.ONE_QUEUE_MODE]:
            group.delay = 3.0
        else:
            group.delay = 0.0
    else:
        group.delay = args.delay
    if args.listener is None:
        args.listener = False
    else:
        group.listener = args.listener
    return group


def parse_default_tmtccmd_input_arguments(
    parser: argparse.ArgumentParser,
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

    if len(unknown) > 0:
        print(f"Unknown arguments detected: {unknown}")
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
        help="Enables interactive or multi-queue mode, where the backend will be configured "
        "to handle multiple queues",
        action="store_true",
        default=False,
    )
    arg_parser.add_argument(
        "-d",
        "--delay",
        type=float,
        help="Default inter-packet delay. Default: 3 seconds for one queue mode, "
        "0 for interactive mode",
        default=None,
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
    help_text += one_q + listener_help + gui_help + multi_q
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
