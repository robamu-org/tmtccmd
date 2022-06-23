from unittest.mock import MagicMock

from tests.hook_obj_mock import TestHookObj
from tests.tc_handler_mock import TcHandler

from tmtccmd.core.ccsds_backend import CcsdsTmtcBackend
from tmtccmd.ccsds.handler import CcsdsTmHandler
from tmtccmd.config.com_if import create_communication_interface_default
from tmtccmd.tm.ccsds_tm_listener import CcsdsTmListener
from tmtccmd.utility.tmtc_printer import FsfwTmTcPrinter, DisplayMode
from tmtccmd.config.definitions import CoreComInterfaces, CoreModeList
from tmtccmd.core.frontend_base import FrontendBase


def create_backend_mock(tm_handler: CcsdsTmHandler) -> CcsdsTmtcBackend:
    hook_obj = TestHookObj()
    tmtc_printer = FsfwTmTcPrinter(display_mode=DisplayMode.LONG, file_logger=None)
    com_if = create_communication_interface_default(
        com_if_key=CoreComInterfaces.DUMMY.value,
        json_cfg_path="tmtc_config.json",
    )
    tc_handler = TcHandler()
    tm_listener = CcsdsTmListener(com_if=com_if, seq_timeout=3.0)
    # The global variables are set by the argument parser.
    tmtc_backend = CcsdsTmtcBackend(
        hook_obj=hook_obj,
        com_if=com_if,
        tm_listener=tm_listener,
        tm_handler=tm_handler,
        tc_handler=tc_handler,
    )
    tmtc_backend.start_listener = MagicMock(return_value=0)
    tmtc_backend.initialize = MagicMock(return_value=0)
    return tmtc_backend


def create_frontend_mock() -> FrontendBase:
    from tmtccmd.core.frontend_base import FrontendBase

    tmtc_frontend = FrontendBase()
    tmtc_frontend.start = MagicMock(return_value=0)
    return tmtc_frontend
