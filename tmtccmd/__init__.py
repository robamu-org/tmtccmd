"""Contains core methods called by entry point files to setup and start a tmtccmd application"""
# I think this needs to be in string representation to be parsed so we can't
# use a formatted string here.
__version__ = "4.0.0a3"
import sys
import os
from datetime import timedelta
from typing import Union, cast, Optional

from tmtccmd.config.args import ProcedureParamsWrapper
from tmtccmd.core.ccsds_backend import CcsdsTmtcBackend
from tmtccmd.core.base import FrontendBase, BackendRequest
from tmtccmd.tm.ccsds_tm_listener import CcsdsTmListener
from tmtccmd.config import (
    HookBase,
    backend_mode_conversion,
    SetupWrapper,
    SetupParams,
    PreArgsParsingWrapper,
    CoreModeConverter,
    CoreModeList,
    DefaultProcedureParams,
)
from tmtccmd.core.ccsds_backend import BackendBase
from tmtccmd.tm import TmTypes, TmHandlerBase, CcsdsTmHandler
from tmtccmd.core.globals_manager import update_global
from tmtccmd.logging import get_console_logger
from tmtccmd.config.globals import set_default_globals_pre_args_parsing
from tmtccmd.core import ModeWrapper
from tmtccmd.tc import (
    DefaultProcedureInfo,
    TcProcedureBase,
    ProcedureWrapper,
    TcHandlerBase,
)


VERSION_MAJOR = 4
VERSION_MINOR = 0
VERSION_REVISION = 0

LOGGER = get_console_logger()

__SETUP_WAS_CALLED = False
__SETUP_FOR_GUI = False


def version() -> str:
    return __version__


def setup(setup_args: SetupWrapper):
    """This function needs to be called first before running the TMTC commander core. The setup
    arguments encapsulate all required arguments for the TMTC commander.

    :param setup_args:     Setup arguments
    """
    global __SETUP_WAS_CALLED, __SETUP_FOR_GUI

    if os.name == "nt":
        import colorama

        colorama.init()
    if setup_args.params.use_gui:
        set_default_globals_pre_args_parsing(setup_args.params.apid)
    if not setup_args.params.use_gui:
        __handle_cli_args_and_globals(setup_args)
    __SETUP_FOR_GUI = setup_args.params.use_gui
    __SETUP_WAS_CALLED = True


def start(
    tmtc_backend: BackendBase,
    hook_obj: HookBase,
    tmtc_frontend: Optional[FrontendBase] = None,
    app_name: str = "TMTC Commander",
):
    """This is the primary function to run the TMTC commander. Users should call this function to
    start the TMTC commander. Please note that :py:func:`setup` needs to be
    called before this function.  You also need to build a TMTC backend
    instance and pass it to this call. You can use :py:func:`create_default_tmtc_backend`
    to create a generic backend.

    :param tmtc_backend:        Custom backend can be passed here. Otherwise, a default backend
                                will be created
    :param hook_obj:
    :param tmtc_frontend:       Custom frontend can be passed here. Otherwise, a default frontend
                                will be created
    :param app_name:            Name of application. Will be displayed in GUI
    :raises RunTimeError:  if :py:func:`setup` was not called before
    :return:
    """
    global __SETUP_WAS_CALLED, __SETUP_FOR_GUI
    if not __SETUP_WAS_CALLED:
        LOGGER.warning("setup_tmtccmd was not called first. Call it first")
        sys.exit(1)
    if __SETUP_FOR_GUI:
        __start_tmtc_commander_qt_gui(
            tmtc_frontend=tmtc_frontend,
            hook_obj=hook_obj,
            tmtc_backend=tmtc_backend,
            app_name=app_name,
        )
    else:
        __start_tmtc_commander_cli(tmtc_backend=tmtc_backend)


def init_printout(use_gui: bool):
    if use_gui:
        print(f"-- tmtccmd v{version()} GUI Mode --")
    else:
        print(f"-- tmtccmd v{version()} CLI Mode --")


# TODO: Remove globals altogether
def __handle_cli_args_and_globals(setup_args: SetupWrapper):
    set_default_globals_pre_args_parsing(setup_args.params.apid)


def __start_tmtc_commander_cli(tmtc_backend: BackendBase):
    tmtc_backend.open_com_if()


def __start_tmtc_commander_qt_gui(
    tmtc_backend: BackendBase,
    hook_obj: HookBase,
    tmtc_frontend: Union[None, FrontendBase] = None,
    app_name: str = "TMTC Commander",
):
    global __SETUP_WAS_CALLED
    try:
        from PyQt5.QtWidgets import QApplication

        if not __SETUP_WAS_CALLED:
            LOGGER.warning("setup_tmtccmd was not called first. Call it first")
            sys.exit(1)
        app = QApplication([app_name])
        if tmtc_frontend is None:
            from tmtccmd.gui import TmTcFrontend
            from tmtccmd.core.ccsds_backend import CcsdsTmtcBackend

            tmtc_frontend = TmTcFrontend(
                hook_obj=hook_obj,
                tmtc_backend=cast(CcsdsTmtcBackend, tmtc_backend),
                app_name=app_name,
            )
        tmtc_frontend.start(app)
    except ImportError as e:
        LOGGER.exception(e)
        sys.exit(1)


def create_default_tmtc_backend(
    setup_wrapper: SetupWrapper,
    tm_handler: TmHandlerBase,
    tc_handler: TcHandlerBase,
    init_procedure: Optional[ProcedureWrapper],
) -> BackendBase:
    """Creates a default TMTC backend instance which can be passed to the tmtccmd runner

    :param init_procedure:
    :param tc_handler:
    :param setup_wrapper:
    :param tm_handler:
    :return:
    """
    global __SETUP_WAS_CALLED

    from typing import cast

    if not __SETUP_WAS_CALLED:
        LOGGER.warning("setup_tmtccmd was not called first. Call it first")
        sys.exit(1)
    if tm_handler is None:
        LOGGER.warning(
            "No TM Handler specified! Make sure to specify at least one TM handler"
        )
        sys.exit(1)
    else:
        if tm_handler.get_type() == TmTypes.CCSDS_SPACE_PACKETS:
            tm_handler = cast(CcsdsTmHandler, tm_handler)
    com_if = setup_wrapper.params.com_if
    if com_if is None:
        com_if = setup_wrapper.hook_obj.assign_communication_interface(
            setup_wrapper.params.com_if_id
        )
    tm_listener = CcsdsTmListener(tm_handler)
    mode_wrapper = ModeWrapper()
    backend_mode_conversion(setup_wrapper.params.mode, mode_wrapper)
    if setup_wrapper.params.mode == CoreModeConverter.get_str(
        CoreModeList.LISTENER_MODE
    ):
        print("-- Backend Listener Mode --")
    elif setup_wrapper.params.mode == CoreModeConverter.get_str(
        CoreModeList.ONE_QUEUE_MODE
    ):
        print("-- One Queue Mode --")
    elif setup_wrapper.params.mode == CoreModeConverter.get_str(
        CoreModeList.MULTI_INTERACTIVE_QUEUE_MODE
    ):
        print("-- Multi Queue Mode --")
    # The global variables are set by the argument parser.
    tmtc_backend = CcsdsTmtcBackend(
        com_if=com_if,
        tm_listener=tm_listener,
        tc_handler=tc_handler,
        tc_mode=mode_wrapper.tc_mode,
        tm_mode=mode_wrapper.tm_mode,
    )
    if setup_wrapper.params.backend_params.listener:
        tmtc_backend.keep_listener_mode = True
    tmtc_backend.inter_cmd_delay = timedelta(
        seconds=setup_wrapper.params.tc_params.delay
    )
    if init_procedure is not None:
        tmtc_backend.current_procedure = init_procedure.base
    return tmtc_backend


def setup_backend_def_procedure(
    backend: CcsdsTmtcBackend, tmtc_params: DefaultProcedureParams
):
    backend.current_procedure = DefaultProcedureInfo(
        tmtc_params.service, tmtc_params.op_code
    )
