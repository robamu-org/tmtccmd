#!/usr/bin/python3
"""
@brief      Core method called by entry point files to initiate the TMTC commander.
            The commander is started by first running initialize_tmtc_commander and then
            running run_tmtc_commander
@details
@manual
@author     R. Mueller
"""
import sys
from typing import Tuple

from tmtccmd.core.hook_base import TmTcHookBase
from tmtccmd.core.definitions import CoreGlobalIds, CoreObjectIds
from tmtccmd.core.globals_manager import update_global, get_global
from tmtccmd.core.object_id_manager import insert_object_ids, insert_object_id
from tmtccmd.defaults.args_parser import parse_input_arguments
from tmtccmd.defaults.object_id_setup import get_core_object_ids
from tmtccmd.utility.tmtcc_logger import set_tmtc_logger, get_logger

logger = get_logger()


def initialize_tmtc_commander(hook_object: TmTcHookBase):
    """
    This function needs to be called first before running the TMTC commander core. A hook
    object handle needs to be passed to this function. The user should implement an own hook class
    instance which in turn implemented TmTcHookBase. An instantiation of the hook object is then
    passed to the core. The hook object ecncapsulates the control of the user over the TMTC
    commander core.

    Example for a simple main function content to use the command line mode:

        hook_obj = MyCustomHookClass()
        initialize_tmtccmd(hook_obj)
        run_tmtc_client(False)

    :param: hook_base:  Instantiation of a custom hook object. The TMTC core will call the various
                        hook functions during program run-time.
    """
    __assign_tmtc_commander_hooks(hook_object=hook_object)


def run_tmtc_commander(use_gui: bool, reduced_printout: bool = False):
    """
    This is the primary function to run the TMTC commander. Users should call this function to
    start the TMTC commander. Please note that assign_tmtc_commander_hooks needs to be called
    before this function.

    Example for a simple main function content to use the command line mode:

        hook_obj = MyCustomHookClass()
        initialize_tmtccmd(hook_obj)
        run_tmtc_client(False)

    :param use_gui:             Specify whether the GUI is used or not
    :param reduced_printout:    It is possible to reduce the initial printout with this flag
    :return:
    """
    __set_up_tmtc_commander(use_gui=use_gui, reduced_printout=reduced_printout)
    if use_gui:
        __start_tmtc_commander_qt_gui()
    else:
        __start_tmtc_commander_cli()


def __assign_tmtc_commander_hooks(hook_object: TmTcHookBase):

    if hook_object is None:
        logger.error("Passed hook base object handle is invalid. Terminating..")
        sys.exit(-1)

    # Check whether all required hook functions have bee implemented properly, Python
    # does not enforce this.
    if hook_object.get_version is None or hook_object.add_globals_pre_args_parsing is None \
            or hook_object.add_globals_post_args_parsing is None:
        logger.error("Passed hook base object handle is invalid. "
                     "Abstract functions have to be implemented!")
        sys.exit(-1)
    # Insert hook object handle into global dictionary so it can be used by the TMTC commander
    update_global(CoreGlobalIds.TMTC_HOOK, hook_object)
    # Set core object IDs
    insert_object_ids(get_core_object_ids())
    # Set object IDs specified by the user.
    insert_object_ids(hook_object.set_object_ids())


def __set_up_tmtc_commander(use_gui: bool, reduced_printout: bool):
    from tmtccmd.core.hook_base import TmTcHookBase
    from typing import cast
    set_tmtc_logger()

    # First, we check whether a hook object was passed to the TMTC commander. This hook object
    # encapsulates control of the commnader core so it is required for proper functioning
    # of the commander core.
    hook_obj_raw = get_global(CoreGlobalIds.TMTC_HOOK)
    if hook_obj_raw is None:
        logger.info("No valid hook object found. "
                    "initialize_tmtc_commander needs to be called first. Terminating..")
        sys.exit(-1)
    hook_obj = cast(TmTcHookBase, hook_obj_raw)

    if not reduced_printout:
        __handle_init_printout(use_gui, hook_obj.get_version())

    logger.info("Starting TMTC Commander..")

    if use_gui:
        hook_obj.add_globals_pre_args_parsing(True)
    else:
        __handle_cli_args_and_globals()


def __handle_init_printout(use_gui: bool, version_tuple: Tuple[str, int, int]):
    print("-- Python TMTC Commander --")
    if use_gui:
        print("-- GUI mode --")
    else:
        print("-- Command line mode --")

    print(f"-- Software version {version_tuple[0]} v{version_tuple[1]}.{version_tuple[2]}--")


def __handle_cli_args_and_globals():
    from typing import cast
    from tmtccmd.core.globals_manager import get_global

    hook_obj = cast(TmTcHookBase, get_global(CoreGlobalIds.TMTC_HOOK))
    logger.info("Setting up pre-globals..")
    hook_obj.add_globals_pre_args_parsing(False)

    logger.info("Parsing input arguments..")
    args = parse_input_arguments()

    logger.info("Setting up post-globals..")
    hook_obj.add_globals_post_args_parsing(args)


def __start_tmtc_commander_cli():
    from tmtccmd.core.backend import TmTcHandler
    hook_obj = get_global(CoreGlobalIds.TMTC_HOOK)
    if not isinstance(hook_obj, TmTcHookBase):
        logger.error("TMTC hook is invalid. Please set it with initialize_tmtc_commander before"
                     "starting the program")
        sys.exit(0)
    service = get_global(CoreGlobalIds.SERVICE)
    op_code = get_global(CoreGlobalIds.OP_CODE)
    # The global variables are set by the argument parser.
    tmtc_handler = TmTcHandler(get_global(CoreGlobalIds.COM_IF), get_global(CoreGlobalIds.MODE),
                               service, op_code)
    tmtc_handler.set_one_shot_or_loop_handling(get_global(CoreGlobalIds.USE_LISTENER_AFTER_OP))
    tmtc_handler.initialize()
    tmtc_handler.start()


def __start_tmtc_commander_qt_gui():
    from tmtccmd.core.frontend import TmTcFrontend
    try:
        from PyQt5.QtWidgets import QApplication
    except ImportError:
        logger.error("PyQt5 module not installed, can't run GUI mode!")
        sys.exit(1)
    app = QApplication(["TMTC Commander"])
    tmtc_gui = TmTcFrontend(get_global(CoreGlobalIds.COM_IF), get_global(CoreGlobalIds.MODE),
                            get_global(CoreGlobalIds.SERVICE))
    tmtc_gui.start_ui()
    sys.exit(app.exec_())



