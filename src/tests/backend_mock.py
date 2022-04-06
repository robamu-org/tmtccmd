from unittest.mock import MagicMock

from tmtccmd.core.backend import TmTcHandler
from tmtccmd.ccsds.handler import CcsdsTmHandler
from tmtccmd.config.com_if import create_communication_interface_default
from tmtccmd.sendreceive.tm_listener import TmListener
from tmtccmd.utility.tmtc_printer import FsfwTmTcPrinter, DisplayMode
from tmtccmd.config.definitions import CoreComInterfaces, CoreModeList
from tmtccmd.core.frontend_base import FrontendBase


def create_backend_mock(tm_handler: CcsdsTmHandler) -> TmTcHandler:
    tmtc_printer = FsfwTmTcPrinter(display_mode=DisplayMode.LONG, file_logger=None)
    com_if = create_communication_interface_default(
        com_if_key=CoreComInterfaces.DUMMY.value,
        json_cfg_path="tmtc_config.json",
    )
    tm_listener = TmListener(com_if=com_if, tm_timeout=3.0, tc_timeout_factor=3.0)
    # The global variables are set by the argument parser.
    tmtc_backend = TmTcHandler(
        com_if=com_if,
        tm_listener=tm_listener,
        init_mode=CoreModeList.IDLE,
        init_service=17,
        init_opcode="0",
        tm_handler=tm_handler,
    )
    tmtc_backend.start_listener = MagicMock(return_value=0)
    tmtc_backend.initialize = MagicMock(return_value=0)
    return tmtc_backend


def create_frontend_mock() -> FrontendBase:
    from tmtccmd.core.frontend_base import FrontendBase

    tmtc_frontend = FrontendBase()
    tmtc_frontend.start = MagicMock(return_value=0)
    return tmtc_frontend
