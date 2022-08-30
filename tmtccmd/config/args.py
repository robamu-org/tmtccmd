"""Argument parser module"""
import argparse
import sys
from typing import Optional, List, Sequence
from dataclasses import dataclass

from prompt_toolkit.shortcuts import CompleteStyle

from tmtccmd.config.prompt import prompt_op_code, prompt_service
from tmtccmd.logging import get_console_logger

from .defs import CoreModeList, CoreComInterfaces, CoreModeConverter
from .hook import TmTcCfgHookBase


LOGGER = get_console_logger()


def get_default_descript_txt() -> str:
    from tmtccmd.util.conf_util import AnsiColors

    return (
        f"{AnsiColors.GREEN}TMTC Client Command Line Interface\n"
        f"{AnsiColors.RESET}This application provides generic components to perform remote\n"
        f"commanding with special support for space applications.\n"
    )


def create_default_args_parser(
    parent_parser: argparse.ArgumentParser,
    descript_txt: Optional[str] = None,
) -> argparse.ArgumentParser:
    if descript_txt is None:
        descript_txt = get_default_descript_txt()
    return argparse.ArgumentParser(
        description=descript_txt,
        formatter_class=argparse.RawTextHelpFormatter,
        parents=[parent_parser],
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
    compl_style: CompleteStyle = CompleteStyle.READLINE_LIKE


class SetupParams:
    def __init__(
        self,
        def_proc_args: Optional[DefProcedureParams] = None,
        tc_params: Optional[TcParams] = None,
        backend_params: Optional[BackendParams] = None,
        app_params: Optional[AppParams] = None,
    ):
        self.def_proc_args = def_proc_args
        if tc_params is None:
            self.tc_params = TcParams()
        if backend_params is None:
            self.backend_params = BackendParams()
        if app_params is None:
            self.app_params = AppParams()

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
    add_default_procedure_arguments(parser)
    add_ethernet_arguments(parser)


def parse_default_tmtccmd_input_arguments(
    args: Sequence[str],
    parser: argparse.ArgumentParser,
    print_known_args: bool = False,
    print_unknown_args: bool = False,
) -> (argparse.Namespace, List[str]):
    """Parses all input arguments
    :return: Input arguments contained in a special namespace and accessable by args.<variable>
    """

    if len(sys.argv) == 1:
        print("No input arguments specified. Run with -h to get list of arguments")

    args, unknown = parser.parse_known_args(args)

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


def add_default_procedure_arguments(parser_or_subparser: argparse.ArgumentParser):
    parser_or_subparser.add_argument(
        "-s",
        "--service",
        help="Procedure service code, used for the default procedure mode",
        default=None,
    )
    parser_or_subparser.add_argument(
        "-o",
        "--op_code",
        help="Procedure operation code, used for the default procedure mode",
        default=None,
    )


def add_cfdp_procedure_arguments(parser_or_subparser: argparse.ArgumentParser):
    """TODO: Could be extended to support the various types of CFDP user primitives.
    Right now, the first thing to be implemented will be the put request"""
    parser_or_subparser.add_argument(
        "file", help="Target file for the CFDP Put Request"
    )
    parser_or_subparser.add_argument(
        "-p",
        "--proxy",
        help="Used to trigger a proxy operation at the remote CFDP entity.\n "
        "Most commonly used to request a file from the remote entity.\n"
        "Please note that this inverses the meaning of the destination and file parameter.",
    )
    parser_or_subparser.add_argument(
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
        "-l",
        "--listener",
        help="The backend will be configured to go into listener mode after "
        "finishing the first queue\nif a service argument is specified. If this flag is specified\n"
        "without the -s flag and none of the queue modes are specified explicitely,\n"
        "the mode will be set to the listener mode",
        action="store_true",
        default=False,
    )
    arg_parser.add_argument(
        "-i",
        "--interactive",
        help="Enables interactive or multi-queue mode, where the backend will be configured\n"
        "to handle multiple queues",
        action="store_true",
        default=False,
    )
    arg_parser.add_argument(
        "-d",
        "--delay",
        type=float,
        help="Default inter-packet delay. Default: 4.0 seconds for one queue mode, "
        "0 for interactive mode",
        default=None,
    )


def add_default_mode_arguments(arg_parser: argparse.ArgumentParser):
    from tmtccmd.config import CoreModeList, CoreModeConverter

    help_text = f"Core Modes. Default: {CoreModeConverter.get_str(CoreModeList.ONE_QUEUE_MODE)}\n"
    one_q = (
        f"{CoreModeList.ONE_QUEUE_MODE} or "
        f"{CoreModeConverter.get_str(CoreModeList.ONE_QUEUE_MODE)}: "
        f"One Queue Command Mode\n"
    )
    listener_help = (
        f"{CoreModeList.LISTENER_MODE} or {CoreModeConverter.get_str(CoreModeList.LISTENER_MODE)}: "
        f"Listener Mode\n"
    )
    multi_q = (
        f"{CoreModeList.MULTI_INTERACTIVE_QUEUE_MODE} or "
        f"{CoreModeConverter.get_str(CoreModeList.MULTI_INTERACTIVE_QUEUE_MODE)}: "
        f"Multi Queue and Interactive Command Mode\n"
    )
    help_text += one_q + listener_help + multi_q
    arg_parser.add_argument(
        "-m",
        "--mode",
        type=str,
        help=help_text,
        default=None,
    )


def add_default_com_if_arguments(arg_parser: argparse.ArgumentParser):
    from tmtccmd.config import CORE_COM_IF_DICT, CoreComInterfaces

    help_text = (
        "Core Communication Interface. If this is not specified, the commander core\n"
        "will try to extract it from the JSON or prompt it from the user. \n"
        "Choices provided by framework: \n"
    )
    for k, v in CORE_COM_IF_DICT.items():
        help_text += f"{k}: {v[0]}\n"
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


def find_service_and_op_code(
    params: SetupParams,
    hook_obj: TmTcCfgHookBase,
    pargs: argparse.Namespace,
    use_prompts: bool,
):
    tmtc_defs = hook_obj.get_tmtc_definitions()
    if pargs.service is None:
        if use_prompts:
            print("No service argument (-s) specified, prompting from user")
            # Try to get the service list from the hook base and prompt service
            # from user
            params.def_proc_args.service = prompt_service(
                tmtc_defs, params.app_params.compl_style
            )
    else:
        params.def_proc_args.service = pargs.service
    if pargs.op_code is None:
        current_service = params.def_proc_args.service
        if use_prompts:
            params.def_proc_args.op_code = prompt_op_code(
                tmtc_defs, current_service, params.app_params.compl_style
            )
    else:
        params.def_proc_args.op_code = pargs.op_code


def args_to_params(
    pargs: argparse.Namespace,
    params: SetupParams,
    hook_obj: TmTcCfgHookBase,
    use_prompts: bool,
):
    """If some arguments are unspecified, they are set here with (variable) default values.

    :param pargs: Parsed arguments from calling parse method
    :param params: Setup parameter object which will be set by this function
    :param hook_obj:
    :param use_prompts: Specify whether terminal prompts are allowed to retrieve unspecified
        arguments. For something like a GUI, it might make sense to disable this
    :return: None
    """
    from tmtccmd.com_if.utils import determine_com_if

    if pargs.gui is None:
        params.app_params.use_gui = False
    else:
        params.app_params.use_gui = pargs.gui
    params.backend_params.listener = pargs.listener
    if pargs.com_if is None or pargs.com_if == CoreComInterfaces.UNSPECIFIED.value:
        params.com_if_id = determine_com_if(
            hook_obj.get_com_if_dict(), hook_obj.json_cfg_path, use_prompts
        )
    else:
        # TODO: Check whether COM IF is valid?
        params.com_if_id = pargs.com_if
    mode_set_explicitely = False
    if pargs.mode is None:
        params.mode = CoreModeConverter.get_str(CoreModeList.ONE_QUEUE_MODE)
    else:
        mode_set_explicitely = True
        params.mode = pargs.mode
    if (
        params.backend_params.listener
        and (not pargs.service and not pargs.op_code)
        and not mode_set_explicitely
    ):
        params.mode = CoreModeConverter.get_str(CoreModeList.LISTENER_MODE)
    tmtc_defs = hook_obj.get_tmtc_definitions()
    params.def_proc_args = DefProcedureParams("0", "0")
    if tmtc_defs is None:
        LOGGER.warning("Invalid Service to Op-Code dictionary detected")
    else:
        if params.mode != CoreModeConverter.get_str(CoreModeList.LISTENER_MODE):
            find_service_and_op_code(
                params=params, hook_obj=hook_obj, use_prompts=use_prompts, pargs=pargs
            )
    if pargs.delay is None:
        if params.backend_params.mode == CoreModeConverter.get_str(
            CoreModeList.ONE_QUEUE_MODE
        ):
            params.tc_params.delay = 4.0
        else:
            params.tc_params.delay = 0.0
    else:
        params.tc_params.delay = float(pargs.delay)


class ArgParserWrapper:
    def __init__(self, hook_obj: TmTcCfgHookBase):
        self.parent_parser: Optional[argparse.ArgumentParser] = None
        self.args_parser: Optional[argparse.ArgumentParser] = None
        self.print_known_args = False
        self.print_unknown_args = False
        self.hook_obj = hook_obj
        self.unknown_args = [""]
        self.args_raw = None
        self._parse_was_called = False
        self._monkey_patch_missing_subparser = False

    def create_default_parent_parser(self):
        """Create a default parent parser, which contains common flags for all possible
        tmtccmd submodules. For example, both the cfdp and default tmtc submodule could contain
        these common flags"""
        self.parent_parser = argparse.ArgumentParser(add_help=False)
        add_default_com_if_arguments(self.parent_parser)
        add_default_mode_arguments(self.parent_parser)
        add_generic_arguments(self.parent_parser)

    def create_default_parser(self):
        """Create the default parser. Requires a valid parent parser containing common flags"""
        if self.parent_parser is None:
            raise ValueError(
                "Create parent parser with create_default_parent_parser or assign a "
                "parent_parser first"
            )
        self.args_parser = create_default_args_parser(
            self.parent_parser, descript_txt=None
        )

    def parse(self):
        if self.parent_parser is None:
            raise ValueError(
                "Create parser with create_default_parser or assign a parser first"
            )
        """Parse all CLI arguments with the given argument parser"""
        if not self._parse_was_called:
            patched_args = None
            if self._monkey_patch_missing_subparser:
                if (
                    len(sys.argv) > 1
                    and sys.argv[1] not in ["cfdp", "tmtc", "-h", "--help"]
                    or len(sys.argv) == 1
                ):
                    print(
                        "No procedure type specified, inserting 'tmtc' into passed arguments"
                    )
                    patched_args = ["tmtc"]
                    patched_args.extend(sys.argv[1:])
            if patched_args is None:
                patched_args = sys.argv[1:]
            self.args_raw, self.unknown_args = parse_default_tmtccmd_input_arguments(
                args=patched_args,
                parser=self.args_parser,
                print_known_args=self.print_known_args,
                print_unknown_args=self.print_unknown_args,
            )
        self._parse_was_called = True

    def add_def_proc_args(self):
        """Add the default tmtc procedure parameters to the default parser. This includes
        the service and operation code flags"""
        self._check_arg_parser()
        add_default_procedure_arguments(self.args_parser)

    def add_cfdp_args(self):
        """Add the default CFDP procedure parameters to the default parser."""
        self._check_arg_parser()
        add_cfdp_procedure_arguments(self.args_parser)

    def _check_arg_parser(self):
        if self.args_parser is None:
            raise ValueError(
                "Please build an argument parser first using the create_default_parser "
                "function or assigning args_parser"
            )

    def add_def_proc_and_cfdp_as_subparsers(self):
        """Add the default tmtc and cfdp procedure as subparsers."""
        self._monkey_patch_missing_subparser = True
        subparser = self.args_parser.add_subparsers(dest="proc_type")
        tmtc_parser = subparser.add_parser(
            "tmtc",
            help="Default TMTC Procedure Mode.\nDefault if no positional argument is specified",
            description="Default TMTC Procedure Mode using a Service and Operation "
            "Code Command Tuple to dispatch commands",
            formatter_class=argparse.RawTextHelpFormatter,
            parents=[self.parent_parser],
        )
        add_default_procedure_arguments(tmtc_parser)
        cfdp_descrip = "CCSDS CFDP File Transfer"
        cfdp_parser = subparser.add_parser(
            "cfdp",
            help=cfdp_descrip,
            description=cfdp_descrip,
            formatter_class=argparse.RawTextHelpFormatter,
            parents=[self.parent_parser],
        )
        add_cfdp_procedure_arguments(cfdp_parser)

    @property
    def use_gui(self):
        """This only yields valid values if :py:meth:`parse` was called once"""
        if not self._parse_was_called:
            return False
        return self.args_raw.gui

    def set_params(self, params: SetupParams):
        """Set up the parameter object from the parsed arguments. This call auto-determines whether
        prompts should be used depending on whether the GUI flag was passed or not.

        :raise Value Error: Parse function call missing
        """
        if not self._parse_was_called:
            raise ValueError("Call the parse function first")
        if self.args_raw.gui:
            self.set_params_without_prompts(params)
        else:
            self.set_params_with_prompts(params)

    def set_params_without_prompts(self, params: SetupParams):
        if not self._parse_was_called:
            raise ValueError("Call the parse function first")
        args_to_params(
            pargs=self.args_raw,
            params=params,
            hook_obj=self.hook_obj,
            use_prompts=False,
        )

    def set_params_with_prompts(self, params: SetupParams):
        if not self._parse_was_called:
            raise ValueError("Call the parse function first")
        try:
            args_to_params(
                pargs=self.args_raw,
                params=params,
                hook_obj=self.hook_obj,
                use_prompts=True,
            )
        except KeyboardInterrupt:
            raise KeyboardInterrupt(
                "Keyboard interrupt while converting CLI args to application parameters"
            )
