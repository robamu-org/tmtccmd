"""Contains core methods called by entry point files to setup and start a tmtccmd application"""
import sys
import os
from typing import Union

from spacepackets.ecss.conf import get_default_tc_apid

from tmtccmd import __version__
from tmtccmd.config import SetupArgs, TmTcHookBase, CoreGlobalIds, pass_cli_args
from tmtccmd.core.backend import BackendBase
from tmtccmd.core.frontend_base import FrontendBase
from tmtccmd.tm.definitions import TmTypes
from tmtccmd.tm.handler import TmHandler
from tmtccmd.ccsds.handler import CcsdsTmHandler
from tmtccmd.core.globals_manager import (
    update_global,
    get_global,
    lock_global_pool,
    unlock_global_pool,
)
from tmtccmd.logging import get_console_logger
from .config.globals import set_default_globals_pre_args_parsing

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
        set_default_globals_pre_args_parsing(
            setup_args.use_gui, tc_apid=setup_args.tc_apid, tm_apid=setup_args.tm_apid
        )
    if not setup_args.use_gui:
        __handle_cli_args_and_globals(setup_args)
    __SETUP_FOR_GUI = setup_args.use_gui
    __SETUP_WAS_CALLED = True


def run(
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
    :param tmtc_frontend:       Custom frontend can be passed here. Otherwise, a default backend
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


def __assign_tmtc_commander_hooks(hook_object: TmTcHookBase):
    if hook_object is None:
        raise ValueError
    # Insert hook object handle into global dictionary so it can be used by the TMTC commander
    update_global(CoreGlobalIds.TMTC_HOOK, hook_object)
    # TODO: Maybe this is not required anymore..
    # Set core object IDs
    # insert_object_ids(get_core_object_ids())
    # Set object IDs specified by the user.
    # insert_object_ids(hook_object.get_object_ids())


def init_printout(use_gui: bool, ansi_colors: bool = True):
    if ansi_colors:
        print(f"-- Python TMTC Commander --")
    if use_gui:
        print("-- GUI mode --")
    else:
        print("-- Command line mode --")

    print(f"-- tmtccmd version v{version()} --")
    LOGGER.info("Starting TMTC Commander..")


def __handle_cli_args_and_globals(setup_args: SetupArgs):
    LOGGER.info("Setting up pre-globals..")
    set_default_globals_pre_args_parsing(
        setup_args.use_gui, tc_apid=setup_args.tc_apid, tm_apid=setup_args.tm_apid
    )
    LOGGER.info("Setting up post-globals..")
    pass_cli_args(setup_args=setup_args)


def __start_tmtc_commander_cli(tmtc_backend: BackendBase):
    __get_backend_init_variables()
    tmtc_backend.initialize()
    tmtc_backend.start_listener()


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
        app = None
        app = QApplication([app_name])
        if tmtc_frontend is None:
            from tmtccmd.core.frontend import TmTcFrontend
            from tmtccmd.config.hook import get_global_hook_obj

            tmtc_frontend = TmTcFrontend(
                hook_obj=get_global_hook_obj(),
                tmtc_backend=tmtc_backend,
                app_name=app_name,
            )
        tmtc_frontend.start(app)
    except ImportError:
        LOGGER.error("PyQt5 module not installed, can't run GUI mode!")
        sys.exit(1)


def __get_backend_init_variables():
    service = get_global(CoreGlobalIds.CURRENT_SERVICE)
    op_code = get_global(CoreGlobalIds.OP_CODE)
    com_if = get_global(CoreGlobalIds.COM_IF)
    mode = get_global(CoreGlobalIds.MODE)
    return service, op_code, com_if, mode


def create_default_tmtc_backend(setup_args: SetupArgs, tm_handler: TmHandler):
    """Creates a default TMTC backend instance which can be passed to the tmtccmd runner

    :param setup_args:
    :param tm_handler:
    :return:
    """
    global __SETUP_WAS_CALLED
    from tmtccmd.core.backend import TmTcHandler
    from tmtccmd.sendreceive.tm_listener import TmListener
    from typing import cast

    if not __SETUP_WAS_CALLED:
        LOGGER.warning("setup_tmtccmd was not called first. Call it first")
        sys.exit(1)
    service, op_code, com_if_id, mode = __get_backend_init_variables()
    if tm_handler is None:
        LOGGER.warning(
            "No TM Handler specified! Make sure to specify at least one TM handler"
        )
        sys.exit(1)
    else:
        if tm_handler.get_type() == TmTypes.CCSDS_SPACE_PACKETS:
            tm_handler = cast(CcsdsTmHandler, tm_handler)
    apid = get_default_tc_apid()
    com_if = setup_args.hook_obj.assign_communication_interface(
        com_if_key=get_global(CoreGlobalIds.COM_IF)
    )
    tc_send_timeout_factor = get_global(CoreGlobalIds.TC_SEND_TIMEOUT_FACTOR)
    tm_timeout = get_global(CoreGlobalIds.TM_TIMEOUT)
    tm_listener = TmListener(
        com_if=com_if, tm_timeout=tm_timeout, tc_timeout_factor=tc_send_timeout_factor
    )
    # The global variables are set by the argument parser.
    tmtc_backend = TmTcHandler(
        com_if=com_if,
        tm_listener=tm_listener,
        init_mode=mode,
        init_service=service,
        init_opcode=op_code,
        tm_handler=tm_handler,
    )
    tmtc_backend.set_current_apid(apid=apid)
    tmtc_backend.set_one_shot_or_loop_handling(
        not get_global(CoreGlobalIds.USE_LISTENER_AFTER_OP)
    )
    return tmtc_backend
