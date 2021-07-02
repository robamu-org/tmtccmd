#!/usr/bin/env python3
"""
Core method called by entry point files to initiate the TMTC commander.
The commander is started by first running `initialize_tmtc_commander` and then
running `run_tmtc_commander`
:details:
:manual:
:author:     R. Mueller
"""
import sys
import os
from typing import Union

from tmtccmd.config.hook import TmTcHookBase
from tmtccmd.core.backend import BackendBase
from tmtccmd.core.frontend_base import FrontendBase
from tmtccmd.config.definitions import CoreGlobalIds
from tmtccmd.tm.definitions import TmTypes
from tmtccmd.tm.handler import TmHandler
from tmtccmd.ccsds.handler import CcsdsTmHandler
from tmtccmd.core.globals_manager import update_global, get_global, lock_global_pool, unlock_global_pool
from tmtccmd.core.object_id_manager import insert_object_ids
from tmtccmd.config.args import parse_input_arguments
from tmtccmd.config.objects import get_core_object_ids
from tmtccmd.utility.logger import set_tmtc_console_logger, get_console_logger
from tmtccmd.utility.conf_util import AnsiColors

LOGGER = get_console_logger()


def initialize_tmtc_commander(hook_object: TmTcHookBase):
    """This function needs to be called first before running the TMTC commander core. A hook
    object handle needs to be passed to this function. The user should implement an own hook class
    instance which in turn implemented TmTcHookBase. An instantiation of the hook object is then
    passed to the core. The hook object ecncapsulates the control of the user over the TMTC
    commander core.

    Example for a simple main function content to use the command line mode:

        hook_obj = MyCustomHookClass()
        initialize_tmtccmd(hook_obj)
        run_tmtc_client(False)

    :param hook_object:     Instantiation of a custom hook object. The TMTC core will call the
                            various hook functions during program run-time.
    :raises: ValueError for an invalid hook object.
    """
    if os.name == 'nt':
        import colorama
        colorama.init()

    __assign_tmtc_commander_hooks(hook_object=hook_object)


def add_ccsds_handler(ccsds_handler: CcsdsTmHandler):
    """Add a handler for CCSDS space packets, for example PUS packets
    :param pus_handler:
    :return:
    """
    lock_global_pool()
    tm_handler = get_global(CoreGlobalIds.TM_HANDLER_HANDLE)
    if tm_handler is None:
        update_global(CoreGlobalIds.TM_HANDLER_HANDLE, ccsds_handler)
    unlock_global_pool()


def run_tmtc_commander(
        use_gui: bool, reduced_printout: bool = False, ansi_colors: bool = True,
        tmtc_backend: Union[BackendBase, None] = None,
        tmtc_frontend: Union[FrontendBase, None] = None,
        app_name: str = "TMTC Commander"
):
    """This is the primary function to run the TMTC commander. Users should call this function to
    start the TMTC commander. Please note that :py:func:`initialize_tmtc_commander` needs to be
    called before this function. Raises RuntimeError if :py:func:`initialize_tmtc_commander`
    has not been called before calling this function.

    :param use_gui:             Specify whether the GUI is used or not
    :param reduced_printout:    It is possible to reduce the initial printout with this flag
    :param ansi_colors:         Enable ANSI color output for terminal
    :param tmtc_backend:        Custom backend can be passed here. Otherwise, a default backend
                                will be created
    :param tmtc_frontend:       Custom frontend can be passed here. Otherwise, a default backend
                                will be created
    :param app_name:            Name of application. Will be displayed in GUI
    :raises: ValueError if :py:func:`initialize_tmtc_commander` was not called before
    :return:
    """
    try:
        __set_up_tmtc_commander(
            use_gui=use_gui, reduced_printout=reduced_printout, ansi_colors=ansi_colors
        )
    except ValueError:
        raise RuntimeError

    if use_gui:
        __start_tmtc_commander_qt_gui(tmtc_frontend=tmtc_frontend, app_name=app_name)
    else:
        if tmtc_backend is None:
            from tmtccmd.config.hook import get_global_hook_obj
            hook_obj = get_global_hook_obj()
            json_cfg_path = hook_obj.get_json_config_file_path()
            tm_handler = get_global(CoreGlobalIds.TM_HANDLER_HANDLE)
            tmtc_backend = get_default_tmtc_backend(
                hook_obj=hook_obj, tm_handler=tm_handler, json_cfg_path=json_cfg_path
            )
        __start_tmtc_commander_cli(tmtc_backend=tmtc_backend)


def __assign_tmtc_commander_hooks(hook_object: TmTcHookBase):
    if hook_object is None:
        raise ValueError

    # Check whether all required hook functions have bee implemented properly, Python
    # does not enforce this.
    if hook_object.get_version is None or hook_object.add_globals_pre_args_parsing is None \
            or hook_object.add_globals_post_args_parsing is None:
        LOGGER.error(
            "Passed hook base object handle is invalid. Abstract functions have to be implemented!"
        )
        raise ValueError
    # Insert hook object handle into global dictionary so it can be used by the TMTC commander
    update_global(CoreGlobalIds.TMTC_HOOK, hook_object)
    # Set core object IDs
    insert_object_ids(get_core_object_ids())
    # Set object IDs specified by the user.
    insert_object_ids(hook_object.get_object_ids())


def __set_up_tmtc_commander(
        use_gui: bool, reduced_printout: bool, ansi_colors: bool = True,
        tmtc_backend: Union[BackendBase, None] = None
):
    """Set up the TMTC commander. Raise ValueError if a passed parameter is invalid.
    :param use_gui:
    :param reduced_printout:
    :param ansi_colors:
    :param tmtc_backend:
    :return:
    """
    from tmtccmd.config.hook import TmTcHookBase
    from typing import cast
    set_tmtc_console_logger()

    # First, we check whether a hook object was passed to the TMTC commander. This hook object
    # encapsulates control of the commnader core so it is required for proper functioning
    # of the commander core.
    hook_obj_raw = get_global(CoreGlobalIds.TMTC_HOOK)
    if hook_obj_raw is None:
        LOGGER.warning(
            "No valid hook object found. initialize_tmtc_commander needs to be called first. "
            "Terminating.."
        )
        raise ValueError
    hook_obj = cast(TmTcHookBase, hook_obj_raw)

    if not reduced_printout:
        __handle_init_printout(use_gui, hook_obj.get_version(), ansi_colors)

    LOGGER.info("Starting TMTC Commander..")

    if use_gui:
        hook_obj.add_globals_pre_args_parsing(True)
    else:
        __handle_cli_args_and_globals()


def __handle_init_printout(use_gui: bool, version_string: str, ansi_colors: bool):
    if ansi_colors:
        print(f'{AnsiColors.CYAN}-- Python TMTC Commander --{AnsiColors.RESET}')
    if use_gui:
        print('-- GUI mode --')
    else:
        print('-- Command line mode --')

    print(f'-- Software version {version_string} --')


def __handle_cli_args_and_globals():
    from typing import cast
    from tmtccmd.core.globals_manager import get_global

    hook_obj = cast(TmTcHookBase, get_global(CoreGlobalIds.TMTC_HOOK))
    LOGGER.info('Setting up pre-globals..')
    hook_obj.add_globals_pre_args_parsing(False)

    LOGGER.info("Parsing input arguments..")
    args = parse_input_arguments()
    LOGGER.info("Setting up post-globals..")
    hook_obj.add_globals_post_args_parsing(args=args)


def __start_tmtc_commander_cli(tmtc_backend: BackendBase):
    __get_backend_init_variables()
    tmtc_backend.initialize()
    tmtc_backend.start_listener()


def __start_tmtc_commander_qt_gui(
        tmtc_frontend: Union[None, FrontendBase] = None, app_name: str = "TMTC Commander"
):
    app = None
    if tmtc_frontend is None:
        from tmtccmd.core.frontend import TmTcFrontend
        from tmtccmd.config.hook import get_global_hook_obj
        try:
            from PyQt5.QtWidgets import QApplication
        except ImportError:
            LOGGER.error("PyQt5 module not installed, can't run GUI mode!")
            sys.exit(1)
        app = QApplication([app_name])
        hook_obj = get_global_hook_obj()
        json_cfg_path = hook_obj.get_json_config_file_path()
        tm_handler = get_global(CoreGlobalIds.TM_HANDLER_HANDLE)
        # The global variables are set by the argument parser.
        tmtc_backend = get_default_tmtc_backend(
            hook_obj=hook_obj, tm_handler=tm_handler, json_cfg_path=json_cfg_path
        )
        tmtc_frontend = TmTcFrontend(
            hook_obj=hook_obj, tmtc_backend=tmtc_backend, app_name=app_name
        )
    tmtc_frontend.start(app)


def __get_backend_init_variables():
    service = get_global(CoreGlobalIds.CURRENT_SERVICE)
    op_code = get_global(CoreGlobalIds.OP_CODE)
    com_if = get_global(CoreGlobalIds.COM_IF)
    mode = get_global(CoreGlobalIds.MODE)
    return service, op_code, com_if, mode


def get_default_tmtc_backend(hook_obj: TmTcHookBase, tm_handler: TmHandler, json_cfg_path: str):
    from tmtccmd.core.backend import TmTcHandler
    from tmtccmd.utility.tmtc_printer import TmTcPrinter
    from tmtccmd.sendreceive.tm_listener import TmListener
    from typing import cast
    service, op_code, com_if_id, mode = __get_backend_init_variables()
    display_mode = get_global(CoreGlobalIds.DISPLAY_MODE)
    print_to_file = get_global(CoreGlobalIds.PRINT_TO_FILE)
    tmtc_printer = TmTcPrinter(display_mode, print_to_file, True)
    if tm_handler is None:
        LOGGER.warning("No TM Handler specified!")
    else:
        if tm_handler.get_type() == TmTypes.CCSDS_SPACE_PACKETS:
            tm_handler = cast(CcsdsTmHandler, tm_handler)
            tm_handler.initialize(tmtc_printer=tmtc_printer)
    apid = get_global(CoreGlobalIds.APID)

    if json_cfg_path:
        pass
    com_if = hook_obj.assign_communication_interface(
        com_if_key=get_global(CoreGlobalIds.COM_IF), tmtc_printer=tmtc_printer
    )
    tc_send_timeout_factor = get_global(CoreGlobalIds.TC_SEND_TIMEOUT_FACTOR)
    tm_timeout = get_global(CoreGlobalIds.TM_TIMEOUT)
    tm_listener = TmListener(
        com_if=com_if, tm_timeout=tm_timeout, tc_timeout_factor=tc_send_timeout_factor
    )
    # The global variables are set by the argument parser.
    tmtc_backend = TmTcHandler(
        com_if=com_if, tmtc_printer=tmtc_printer, tm_listener=tm_listener, init_mode=mode,
        init_service=service, init_opcode=op_code, tm_handler=tm_handler
    )
    tmtc_backend.set_current_apid(apid=apid)
    tmtc_backend.set_one_shot_or_loop_handling(get_global(CoreGlobalIds.USE_LISTENER_AFTER_OP))
    return tmtc_backend
