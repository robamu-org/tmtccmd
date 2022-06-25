"""Contains core methods called by entry point files to setup and start a tmtccmd application"""
import sys
import os
from typing import Union, cast

from tmtccmd import __version__
from tmtccmd.core.ccsds_backend import CcsdsTmtcBackend
from tmtccmd.tm.ccsds_tm_listener import CcsdsTmListener
from tmtccmd.config import TmTcCfgHookBase, CoreGlobalIds
from tmtccmd.config.setup import SetupArgs
from tmtccmd.core.ccsds_backend import BackendBase
from tmtccmd.core.frontend_base import FrontendBase
from tmtccmd.tm.definitions import TmTypes
from tmtccmd.tm.handler import TmHandlerBase
from tmtccmd.ccsds.handler import CcsdsTmHandler
from tmtccmd.core.globals_manager import (
    update_global,
    get_global,
    lock_global_pool,
    unlock_global_pool,
)
from tmtccmd.logging import get_console_logger
from .config.definitions import backend_mode_conversion
from .config.globals import set_default_globals_pre_args_parsing
from .core.modes import ModeWrapper
from .tc.definitions import ProcedureInfo
from .tc.handler import TcHandlerBase

LOGGER = get_console_logger()

__SETUP_WAS_CALLED = False
__SETUP_FOR_GUI = False


def version() -> str:
    return __version__


def add_ccsds_handler(ccsds_handler: CcsdsTmHandler):
    """Add a handler for CCSDS space packets, for example PUS packets

    :param ccsds_handler: CCSDS handler for all CCSDS packets, e.g. Space Packets
    :return:
    """
    lock_global_pool()
    tm_handler = get_global(CoreGlobalIds.TM_HANDLER_HANDLE)
    if tm_handler is None:
        update_global(CoreGlobalIds.TM_HANDLER_HANDLE, ccsds_handler)
    unlock_global_pool()


def setup(setup_args: SetupArgs):
    """This function needs to be called first before running the TMTC commander core. The setup
    arguments encapsulate all required arguments for the TMTC commander.

    :param setup_args:     Setup arguments
    """
    global __SETUP_WAS_CALLED, __SETUP_FOR_GUI

    if os.name == "nt":
        import colorama

        colorama.init()

    __assign_tmtc_commander_hooks(hook_object=setup_args.hook_obj)

    if setup_args.use_gui:
        set_default_globals_pre_args_parsing(setup_args.apid)
    if not setup_args.use_gui:
        __handle_cli_args_and_globals(setup_args)
    __SETUP_FOR_GUI = setup_args.use_gui
    __SETUP_WAS_CALLED = True


def start(
    tmtc_backend: BackendBase,
    tmtc_frontend: Union[FrontendBase, None] = None,
    app_name: str = "TMTC Commander",
):
    """This is the primary function to run the TMTC commander. Users should call this function to
    start the TMTC commander. Please note that :py:func:`setup` needs to be
    called before this function.  You also need to build a TMTC backend
    instance and pass it to this call. You can use :py:func:`create_default_tmtc_backend`
    to create a generic backend.

    :param tmtc_backend:        Custom backend can be passed here. Otherwise, a default backend
                                will be created
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
            tmtc_frontend=tmtc_frontend, tmtc_backend=tmtc_backend, app_name=app_name
        )
    else:
        __start_tmtc_commander_cli(tmtc_backend=tmtc_backend)


def init_and_start_daemons(tmtc_backend: BackendBase):
    if __SETUP_FOR_GUI:
        LOGGER.error("daemon mode only supported in cli mode")
        sys.exit(1)
    __start_tmtc_commander_cli(tmtc_backend=tmtc_backend, perform_op_immediately=False)


def __assign_tmtc_commander_hooks(hook_object: TmTcCfgHookBase):
    if hook_object is None:
        raise ValueError
    # Insert hook object handle into global dictionary so it can be used by the TMTC commander
    update_global(CoreGlobalIds.TMTC_HOOK, hook_object)


def init_printout(use_gui: bool):
    if use_gui:
        print(f"-- tmtccmd v{version()} GUI Mode --")
    else:
        print(f"-- tmtccmd v{version()} CLI Mode --")


def __handle_cli_args_and_globals(setup_args: SetupArgs):
    LOGGER.info("Setting up pre-globals..")
    set_default_globals_pre_args_parsing(setup_args.apid)
    LOGGER.info("Setting up post-globals..")


def __start_tmtc_commander_cli(
    tmtc_backend: BackendBase, perform_op_immediately: bool = True
):
    # __get_backend_init_variables()
    tmtc_backend.start_listener(perform_op_immediately)


def __start_tmtc_commander_qt_gui(
    tmtc_backend: BackendBase,
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
            from tmtccmd.core.frontend import TmTcFrontend
            from tmtccmd.config.cfg_hook import get_global_hook_obj
            from tmtccmd.core.ccsds_backend import CcsdsTmtcBackend

            tmtc_frontend = TmTcFrontend(
                hook_obj=get_global_hook_obj(),
                tmtc_backend=cast(CcsdsTmtcBackend, tmtc_backend),
                app_name=app_name,
            )
        tmtc_frontend.start(app)
    except ImportError:
        LOGGER.error("PyQt5 module not installed, can't run GUI mode!")
        sys.exit(1)


"""
def __get_backend_init_variables():
    service = get_global(CoreGlobalIds.CURRENT_SERVICE)
    op_code = get_global(CoreGlobalIds.OP_CODE)
    com_if = get_global(CoreGlobalIds.COM_IF)
    mode = get_global(CoreGlobalIds.MODE)
    return service, op_code, com_if, mode
"""


def create_default_tmtc_backend(
    setup_args: SetupArgs, tm_handler: TmHandlerBase, tc_handler: TcHandlerBase
) -> BackendBase:
    """Creates a default TMTC backend instance which can be passed to the tmtccmd runner

    :param tc_handler:
    :param setup_args:
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
    com_if = setup_args.hook_obj.assign_communication_interface(
        com_if_key=setup_args.args_wrapper.com_if
    )
    tm_listener = CcsdsTmListener(com_if=com_if, tm_handler=tm_handler)
    mode_wrapper = ModeWrapper()
    backend_mode_conversion(setup_args.args_wrapper.mode, mode_wrapper)
    # The global variables are set by the argument parser.
    tmtc_backend = CcsdsTmtcBackend(
        com_if=com_if,
        tm_listener=tm_listener,
        tc_handler=tc_handler,
        tc_mode=mode_wrapper.tc_mode,
        tm_mode=mode_wrapper.tm_mode,
    )
    tmtc_backend.inter_cmd_delay = setup_args.args_wrapper.delay
    tmtc_backend.current_proc_info = ProcedureInfo(
        setup_args.args_wrapper.service, setup_args.args_wrapper.op_code
    )
    return tmtc_backend
