"""Argument parser module"""
import argparse
import sys
from typing import Optional, List
from dataclasses import dataclass
from tmtccmd.logging import get_console_logger


LOGGER = get_console_logger()


def get_default_descript_txt() -> str:
    from tmtccmd.utility.conf_util import AnsiColors

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
class DefProcedureParams:
    service: str
    op_code: str


@dataclass
class TcParams:
    delay: float = 0.0
    apid: int = 0


@dataclass
class BackendParams:
    mode: str = ""
    com_if_id: str = ""
    listener: bool = False
    interactive: bool = False


@dataclass
class AppParams:
    use_gui: bool = False
    reduced_printout: bool = False
    use_ansi_colors: bool = True


class SetupParams:
    def __init__(
        self,
        def_proc_args: Optional[DefProcedureParams] = None,
        tc_params: TcParams = TcParams(),
        backend_params: BackendParams = BackendParams(),
        app_params: AppParams = AppParams(),
    ):
        self.def_proc_args = def_proc_args
        self.tc_params = tc_params
        self.backend_params = backend_params
        self.app_params = app_params

    @property
    def apid(self):
        return self.tc_params.apid

    @apid.setter
    def apid(self, apid):
        self.tc_params.apid = apid

    @property
    def use_gui(self):
        return self.app_params.use_gui

    @use_gui.setter
    def use_gui(self, use_gui):
        self.app_params.use_gui = use_gui

    @property
    def mode(self):
        return self.backend_params.mode

    @mode.setter
    def mode(self, mode: str):
        self.backend_params.mode = mode

    @property
    def com_if_id(self):
        return self.backend_params.com_if_id

    @com_if_id.setter
    def com_if_id(self, com_if_id):
        self.backend_params.com_if_id = com_if_id


def add_default_tmtccmd_args(parser: argparse.ArgumentParser):
    add_default_mode_arguments(parser)
    add_default_com_if_arguments(parser)
    add_generic_arguments(parser)
    add_cfdp_parser(parser)

    add_ethernet_arguments(parser)


def parse_default_tmtccmd_input_arguments(
    parser: argparse.ArgumentParser,
    print_known_args: bool = False,
    print_unknown_args: bool = False,
) -> (argparse.Namespace, List[str]):
    """Parses all input arguments
    :return: Input arguments contained in a special namespace and accessable by args.<variable>
    """

    if len(sys.argv) == 1:
        print("No input arguments specified. Run with -h to get list of arguments")

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
        "-g", "--gui", help="Use GUI mode", action="store_true", default=False
    )
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
    from tmtccmd.config import CoreModeList, CoreModeStrings

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
    help_text += one_q + listener_help + multi_q
    arg_parser.add_argument(
        "-m",
        "--mode",
        type=str,
        help=help_text,
        default=CoreModeStrings[CoreModeList.ONE_QUEUE_MODE],
    )


def add_default_com_if_arguments(arg_parser: argparse.ArgumentParser):
    from tmtccmd.config import CORE_COM_IF_DICT, CoreComInterfaces

    help_text = (
        "Core Communication Interface. If this is not specified, the commander core\n"
        "will try to extract it from the JSON or prompt it from the user\n"
    )
    dummy_line = f"{CORE_COM_IF_DICT[CoreComInterfaces.DUMMY.value]}: Dummy Interface\n"
    udp_line = f"{CORE_COM_IF_DICT[CoreComInterfaces.UDP.value]}: " f"UDP client\n"
    ser_dle_line = (
        f"{CORE_COM_IF_DICT[CoreComInterfaces.SERIAL_DLE.value]}: "
        f"Serial with DLE transport layer\n"
    )
    ser_fixed_line = (
        f"{CORE_COM_IF_DICT[CoreComInterfaces.SERIAL_FIXED_FRAME.value]}: "
        f"Serial with fixed frames\n"
    )
    ser_qemu_line = (
        f"{CORE_COM_IF_DICT[CoreComInterfaces.SERIAL_QEMU.value]}: "
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
