from unittest.mock import MagicMock
from argparse import Namespace
from tmtccmd.core.backend import TmTcHandler
from tmtccmd.config.hook import TmTcHookBase
from tmtccmd.ccsds.handler import CcsdsTmHandler
from tmtccmd.config.com_if import create_communication_interface_default
from tmtccmd.sendreceive.tm_listener import TmListener
from tmtccmd.utility.tmtc_printer import TmTcPrinter, DisplayMode
from tmtccmd.config.definitions import CoreComInterfaces, CoreModeList
from tmtccmd.core.frontend_base import FrontendBase


def create_hook_mock() -> TmTcHookBase:
    tmtc_hook_base = TmTcHookBase()
    tmtc_hook_base.add_globals_pre_args_parsing = MagicMock(return_value=0)
    tmtc_hook_base.add_globals_post_args_parsing = MagicMock(return_value=0)
    tmtc_hook_base.custom_args_parsing = MagicMock(
        return_value=Namespace(service=17, mode=CoreModeList.IDLE)
    )
    return tmtc_hook_base


def create_backend_mock(tm_handler: CcsdsTmHandler) -> TmTcHandler:
    tmtc_printer = TmTcPrinter(display_mode=DisplayMode.LONG, do_print_to_file=False, print_tc=True)
    com_if = create_communication_interface_default(
        com_if_key=CoreComInterfaces.DUMMY.value, json_cfg_path="tmtc_config.json", tmtc_printer=tmtc_printer
    )
    tm_listener = TmListener(
        com_if=com_if, tm_timeout=3.0, tc_timeout_factor=3.0
    )
    # The global variables are set by the argument parser.
    tmtc_backend = TmTcHandler(
        com_if=com_if, tmtc_printer=tmtc_printer, tm_listener=tm_listener, init_mode=CoreModeList.IDLE,
        init_service=17, init_opcode="0", tm_handler=tm_handler
    )
    tmtc_backend.start_listener = MagicMock(return_value=0)
    tmtc_backend.initialize = MagicMock(return_value=0)
    return tmtc_backend


def create_frontend_mock() -> FrontendBase:
    from tmtccmd.core.frontend_base import FrontendBase
    tmtc_frontend = FrontendBase()
    tmtc_frontend.start = MagicMock(return_value=0)
    return tmtc_frontend
