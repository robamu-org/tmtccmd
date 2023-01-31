"""Argument parser module."""
from __future__ import annotations
import argparse
import sys
from typing import Optional, List, Sequence, Union
from dataclasses import dataclass

from prompt_toolkit.shortcuts import CompleteStyle

from spacepackets.cfdp import TransmissionMode
from tmtccmd.com.utils import determine_com_if
from tmtccmd.tc.procedure import TcProcedureType
from tmtccmd.config.prompt import prompt_op_code, prompt_service
from tmtccmd.logging import get_console_logger

from .defs import CoreModeList, CoreComInterfaces, CoreModeConverter
from .hook import HookBase
from ..com import ComInterface

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
class DefaultProcedureParams:
    service: Optional[str] = None
    op_code: Optional[str] = None


@dataclass
class CfdpParams:
    source = ""
    target = ""
    closure_requested = False
    transmission_mode = TransmissionMode.UNACKNOWLEDGED


class ProcedureParamsWrapper:
    def __init__(self):
        self._ptype = TcProcedureType.CUSTOM
        self._params = None

    @property
    def ptype(self):
        return self._ptype

    def set_params(self, params: Union[DefaultProcedureParams, CfdpParams]):
        if isinstance(params, DefaultProcedureParams):
            self._params = params
            self._ptype = TcProcedureType.DEFAULT
        elif isinstance(params, CfdpParams):
            self._params = params
            self._ptype = TcProcedureType.CFDP

    def def_params(self) -> Optional[DefaultProcedureParams]:
        if self._ptype == TcProcedureType.DEFAULT:
            return self._params
        return None

    def cfdp_params(self) -> Optional[CfdpParams]:
        if self._ptype == TcProcedureType.CFDP:
            return self._params
        return None


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
        com_if: Optional[ComInterface] = None,
        tc_params: Optional[TcParams] = None,
        backend_params: Optional[BackendParams] = None,
        app_params: Optional[AppParams] = None,
    ):
        self.com_if = com_if
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
    add_tmtc_mode_arguments(parser)
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
    """Parses all input arguments by calling :py:meth:`argparse.ArgumentParser.parse_known_args`.
    It is recommended to use the :py:class:`PreArgsParsingWrapper` instead of using this function
    directly.

    :param args: The actual full list of parse CLI arguments
    :param parser: The parser to be used.
    :param print_known_args: Debugging function to print all known arguments.
    :param print_unknown_args:
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
    add_tmtc_mode_arguments(parser_or_subparser)
    add_tmtc_listener_arg(parser_or_subparser)


def add_cfdp_procedure_arguments(parser_or_subparser: argparse.ArgumentParser):
    """TODO: Could be extended to support the various types of CFDP user primitives.
    Right now, the first thing to be implemented will be the put request"""
    parser_or_subparser.add_argument(
        "source", help="Full Source Path for File Copy Procedures", nargs="?"
    )
    parser_or_subparser.add_argument(
        "target", help="Full Destination Path for File Copy Procedures", nargs="?"
    )
    parser_or_subparser.add_argument(
        "-p",
        "--proxy",
        help="Used to trigger a proxy operation at the remote CFDP entity.\n"
        "Most commonly used to request a file from the remote entity.\n"
        "Please note that this inverses the meaning of the destination and file parameter.",
    )
    parser_or_subparser.add_argument(
        "-t",
        "--type",
        help=(
            "Specify the transfer type\n"
            ' - "0" or "ack" for unacknowledged (Class 0) transfers\n'
            ' - "1" or "nak" for acknowledged (Class 1) transfers. Default value'
        ),
        default="nak",
    )
    parser_or_subparser.add_argument(
        "--no-closure",
        help="Disable the requesting of transaction closure",
        action="store_true",
        dest="no_closure",
    )


def add_generic_arguments(arg_parser: argparse.ArgumentParser):
    arg_parser.add_argument(
        "-g", "--gui", help="Use GUI mode", action="store_true", default=False
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
        help=(
            "Default inter-packet delay. Default:\n"
            " - Default One-Queue Mode: 4 seconds\n"
            " - Multi-Queue Mode: 0 seconds"
        ),
        default=None,
    )


def add_tmtc_mode_arguments(arg_parser: argparse.ArgumentParser):
    from tmtccmd.config import CoreModeList, CoreModeConverter

    help_text = f"Core Modes. Default: {CoreModeConverter.get_str(CoreModeList.ONE_QUEUE_MODE)}\n"
    one_q = (
        f' - "{CoreModeList.ONE_QUEUE_MODE}" or '
        f'"{CoreModeConverter.get_str(CoreModeList.ONE_QUEUE_MODE)}": '
        f"One Queue Command Mode\n"
    )
    listener_help = (
        f' - "{CoreModeList.LISTENER_MODE}" or '
        f'"{CoreModeConverter.get_str(CoreModeList.LISTENER_MODE)}": Listener Mode\n'
    )
    multi_q = (
        f' - "{CoreModeList.MULTI_INTERACTIVE_QUEUE_MODE}" or '
        f'"{CoreModeConverter.get_str(CoreModeList.MULTI_INTERACTIVE_QUEUE_MODE)}": '
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


def add_tmtc_listener_arg(arg_parser: argparse.ArgumentParser):
    arg_parser.add_argument(
        "-l",
        "--listener",
        help=(
            "The backend will be configured to go into listener mode after finishing the\n"
            "first queue if a service argument is specified. If this flag is specified\n"
            "without the -s flag and none of the queue modes are specified explicitly,\n"
            "the mode will be set to the listener mode"
        ),
        action="store_true",
        default=False,
    )
    arg_parser.add_argument(
        "--pp",
        "--prompt-proc",
        help=(
            "If this is specified in addition to the listener mode flag -l, the commander will\n"
            "try to determine a service and operation code"
        ),
        dest="prompt_proc",
        action="store_true",
        default=False,
    )


def add_default_com_if_arguments(arg_parser: argparse.ArgumentParser):
    from tmtccmd.config import CORE_COM_IF_DICT, CoreComInterfaces

    help_text = (
        "Core Communication Interface. If this is not specified, the commander core\n"
        "will try to extract it from the JSON or prompt it from the user.\n"
        "Choices provided by framework:\n"
    )
    for k, v in CORE_COM_IF_DICT.items():
        help_text += f' - "{k}": {v[0]}\n'
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
    def_params: DefaultProcedureParams,
    hook_obj: HookBase,
    pargs: argparse.Namespace,
    use_prompts: bool,
):
    tmtc_defs = hook_obj.get_tmtc_definitions()
    if pargs.service is None:
        if use_prompts:
            print("No service argument (-s) specified, prompting from user")
            # Try to get the service list from the hook base and prompt service
            # from user
            def_params.service = prompt_service(
                tmtc_defs, params.app_params.compl_style
            )
    else:
        def_params.service = pargs.service
    if pargs.op_code is None:
        current_service = def_params.service
        if use_prompts:
            def_params.op_code = prompt_op_code(
                tmtc_defs, current_service, params.app_params.compl_style
            )
    else:
        def_params.op_code = pargs.op_code


def args_to_params_generic(
    pargs: argparse.Namespace,
    params: SetupParams,
    hook_obj: HookBase,
    use_prompts: bool,
):
    if pargs.gui is None:
        params.app_params.use_gui = False
    else:
        params.app_params.use_gui = pargs.gui
    if pargs.com_if is None or pargs.com_if == CoreComInterfaces.UNSPECIFIED.value:
        params.com_if_id = determine_com_if(
            hook_obj.get_com_if_dict(), hook_obj.cfg_path, use_prompts
        )
    else:
        params.com_if_id = pargs.com_if


def args_to_params_cfdp(
    pargs: argparse.Namespace,
    params: SetupParams,
    cfdp_params: CfdpParams,
    hook_obj: HookBase,
    use_prompts: bool,
):
    """Helper function to convert CFDP command line arguments to CFDP setup parameters."""
    args_to_params_generic(pargs, params, hook_obj, use_prompts)
    cfdp_params.source = pargs.source
    cfdp_params.target = pargs.target
    cfdp_params.closure_requested = not pargs.no_closure
    if pargs.type in ["0", "nak"]:
        cfdp_params.transmission_mode = TransmissionMode.UNACKNOWLEDGED
    elif pargs.type in ["1", "ack"]:
        cfdp_params.transmission_mode = TransmissionMode.ACKNOWLEDGED
    # TODO: Listener mode is also relevant.
    #       Basically, if -l is specified, use listener after mqueue mode or right aways when
    #       no transaction parameter are specified
    #       Not sure if one queue mode is relevant here. A file transfer might always be split up
    #       in multiple queue fragments and might require feedback before finishing properly.
    params.backend_params.mode = CoreModeConverter.get_str(
        CoreModeList.MULTI_INTERACTIVE_QUEUE_MODE
    )
    if pargs.delay is None:
        params.tc_params.delay = 0.4
    else:
        params.tc_params.delay = float(pargs.delay)


def args_to_params_tmtc(
    pargs: argparse.Namespace,
    params: SetupParams,
    def_tmtc_params: DefaultProcedureParams,
    hook_obj: HookBase,
    use_prompts: bool,
    assign_com_if: bool,
):
    """This function converts command line arguments to the internalized setup parameters.

    It is recommended to use the :py:class:`PostArgsParsingHelper` class to do this instead of
    calling this function directly.

    If some arguments are unspecified, they are set here with (variable) default values.

    :param pargs: Parsed arguments from calling parse method
    :param params: Setup parameter object which will be set by this function
    :param hook_obj:
    :param def_tmtc_params:
    :param use_prompts: Specify whether terminal prompts are allowed to retrieve unspecified
        arguments. For something like a GUI, it might make sense to disable this
    :param assign_com_if: Specifies whether this function should try to determine the COM interface
        from the specified key.
    :return: None
    """
    params.backend_params.listener = pargs.listener
    args_to_params_generic(pargs, params, hook_obj, use_prompts)
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
        and (not pargs.prompt_proc)
    ):
        params.mode = CoreModeConverter.get_str(CoreModeList.LISTENER_MODE)
    if pargs.delay is None:
        if params.backend_params.mode == CoreModeConverter.get_str(
            CoreModeList.ONE_QUEUE_MODE
        ):
            params.tc_params.delay = 4.0
        else:
            params.tc_params.delay = 0.0
    else:
        params.tc_params.delay = float(pargs.delay)
    if assign_com_if:
        params.com_if = hook_obj.assign_communication_interface(params.com_if_id)
    tmtc_defs = hook_obj.get_tmtc_definitions()
    if tmtc_defs is None:
        LOGGER.warning("Invalid Service to Op-Code dictionary detected")
    else:
        if params.mode != CoreModeConverter.get_str(CoreModeList.LISTENER_MODE):
            find_service_and_op_code(
                params=params,
                hook_obj=hook_obj,
                use_prompts=use_prompts,
                pargs=pargs,
                def_params=def_tmtc_params,
            )


class PreArgsParsingWrapper:
    """This class can be used to simplify parsing all tmtccmd CLI arguments.

    It wraps a parent parser and an argument parser but is also able to create default parsers.
    The :py:meth:`parse` method can be used to convert
    this parse the CLI arguments and then create a :py:class:`PostArgsParsingWrapper` to process
    these arguments.

    Please note that the parent parser and argument parser field have to be set or created
    first after creating this wrapper. They can be created by calling
    :py:meth:`create_default_parent_parser` and the :py:meth:`create_default_parser`, but the
    second function requires the parent parser to be set or created first.
    """

    def __init__(self):
        self.parent_parser: Optional[argparse.ArgumentParser] = None
        self.args_parser: Optional[argparse.ArgumentParser] = None
        self.print_known_args = False
        self.print_unknown_args = False
        self._parse_was_called = False
        self._monkey_patch_missing_subparser = False

    def create_default_parent_parser(self):
        """Create a default parent parser, which contains common flags for all possible
        tmtccmd submodules. For example, both the cfdp and default tmtc submodule could contain
        these common flags. The user can extend or modify the parent parser after it was created.
        """
        self.parent_parser = argparse.ArgumentParser(add_help=False)
        add_default_com_if_arguments(self.parent_parser)
        add_generic_arguments(self.parent_parser)

    def create_default_parser(self):
        """Create the default parser. Requires a valid parent parser containing common flags,
        The user can create or modify the parser after it was created. This function requires
        a valid parent parser to be set or created via :py:meth:`create_default_parent_parser`.
        """
        if self.parent_parser is None:
            raise ValueError(
                "Create parent parser with create_default_parent_parser or assign a "
                "parent_parser first"
            )
        self.args_parser = create_default_args_parser(
            self.parent_parser, descript_txt=None
        )

    def parse(
        self, hook_obj: HookBase, setup_params: SetupParams
    ) -> PostArgsParsingWrapper:
        """Parses the set parser by calling the
        :py:meth:`argparse.ArgumentParser.parse_known_args` method internally and returns the
        :py:class:`PostArgsParsingWrapper` to simplify processing the arguments.
        """
        if self.parent_parser is None:
            raise ValueError(
                "Create parser with create_default_parser or assign a parser first"
            )
        """Parse all CLI arguments with the given argument parser"""
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
        args_raw, unknown_args = parse_default_tmtccmd_input_arguments(
            args=patched_args,
            parser=self.args_parser,
            print_known_args=self.print_known_args,
            print_unknown_args=self.print_unknown_args,
        )
        return PostArgsParsingWrapper(
            args_raw=args_raw,
            unknown_args=unknown_args,
            hook_obj=hook_obj,
            params=setup_params,
        )

    def add_def_proc_args(self):
        """Add the default tmtc procedure parameters to the default parser. This includes
        the service and operation code flags."""
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


class PostArgsParsingWrapper:
    """This helper class helps with the internalization of the parse arguments into the format
    expected by tmtccmd.

    :var assign_com_if: If this is set to True (default), the wrapper will try to create
        a :py:class:`tmtccmd.com.ComInterface` on the conversion methods.
    """

    def __init__(
        self,
        args_raw: argparse.Namespace,
        unknown_args: List[str],
        params: SetupParams,
        hook_obj: HookBase,
    ):
        """It is recommended to use :py:meth:`PreArgsParsingWrapper.parse` to retrieve an instance
        instead of using the constructor directly.

        :param args_raw:
        :param unknown_args:
        :param params:
        :param hook_obj:
        """
        self.args_raw = args_raw
        self.params = params
        self.unknown_args = unknown_args
        self.hook_obj = hook_obj
        self.assign_com_if = True

    @property
    def use_gui(self):
        """This only yields valid values if :py:meth:`parse` was called once"""
        return self.args_raw.gui

    def request_type_from_args(self) -> TcProcedureType:
        if hasattr(self.args_raw, "proc_type"):
            if self.args_raw.proc_type == "tmtc":
                return TcProcedureType.DEFAULT
            elif self.args_raw.proc_type == "cfdp":
                return TcProcedureType.CFDP
            else:
                raise ValueError(
                    'Procedure type argument destination unknown, should be "tmtc" or "cfdp"'
                )
        else:
            return TcProcedureType.DEFAULT

    def set_params_with_prompts(self, proc_base: ProcedureParamsWrapper):
        self._set_params(proc_base, True)

    def set_params_without_prompts(self, proc_wrapper: ProcedureParamsWrapper):
        self._set_params(proc_wrapper, False)

    def _set_params(self, proc_base: ProcedureParamsWrapper, with_prompts: bool):
        param_type = self.request_type_from_args()
        if param_type == TcProcedureType.DEFAULT:
            def_proc_params = DefaultProcedureParams()
            if with_prompts:
                self.set_tmtc_params_with_prompts(def_proc_params)
            else:
                self.set_tmtc_params_without_prompts(def_proc_params)
            proc_base.set_params(def_proc_params)
        elif param_type == TcProcedureType.CFDP:
            cfdp_params = CfdpParams()
            if with_prompts:
                self.set_cfdp_params_with_prompts(cfdp_params)
            else:
                self.set_cfdp_params_without_prompts(cfdp_params)
            proc_base.set_params(cfdp_params)

    def set_cfdp_params_with_prompts(self, cfdp_params: CfdpParams):
        self._set_cfdp_params(cfdp_params, True)

    def set_cfdp_params_without_prompts(self, cfdp_params: CfdpParams):
        self._set_cfdp_params(cfdp_params, False)

    def set_tmtc_params_with_prompts(self, tmtc_params: DefaultProcedureParams):
        self._set_tmtc_params(tmtc_params, True)

    def set_tmtc_params_without_prompts(self, tmtc_params: DefaultProcedureParams):
        """Set up the parameter object from the parsed arguments. This call auto-determines whether
        prompts should be used depending on whether the GUI flag was passed or not.

        :raise Value Error: Parse function call missing
        """
        self._set_tmtc_params(tmtc_params, False)

    def _set_tmtc_params(
        self,
        def_tmtc_params: DefaultProcedureParams,
        use_prompts: bool,
    ):
        try:
            args_to_params_tmtc(
                pargs=self.args_raw,
                params=self.params,
                hook_obj=self.hook_obj,
                use_prompts=use_prompts,
                def_tmtc_params=def_tmtc_params,
                assign_com_if=self.assign_com_if,
            )
        except KeyboardInterrupt:
            raise KeyboardInterrupt(
                "Keyboard interrupt while converting CLI args to application parameters"
            )

    def _set_cfdp_params(self, cfdp_params: CfdpParams, use_prompts: bool):
        try:
            args_to_params_cfdp(
                pargs=self.args_raw,
                cfdp_params=cfdp_params,
                params=self.params,
                hook_obj=self.hook_obj,
                use_prompts=use_prompts,
            )
        except KeyboardInterrupt:
            raise KeyboardInterrupt(
                "Keyboard interrupt while converting CLI args to application parameters"
            )
