from unittest.mock import MagicMock
from argparse import Namespace
from tmtccmd.core.backend import TmTcHandler
from tmtccmd.config.hook import TmTcHookBase
from tmtccmd.config.definitions import CoreComInterfaces, CoreModeList, CoreServiceList
from tmtccmd.core.frontend_base import FrontendBase


def create_hook_mock() -> TmTcHookBase:
    tmtc_hook_base = TmTcHookBase()
    tmtc_hook_base.add_globals_pre_args_parsing = MagicMock(return_value=0)
    tmtc_hook_base.add_globals_post_args_parsing = MagicMock(return_value=0)
    tmtc_hook_base.custom_args_parsing = MagicMock(
        return_value=Namespace(service=17, mode=CoreModeList.IDLE)
    )
    return tmtc_hook_base


def create_backend_mock() -> TmTcHandler:
    tmtc_backend = TmTcHandler(
        init_com_if=CoreComInterfaces.DUMMY, init_mode=CoreModeList.IDLE,
        init_service=CoreServiceList.SERVICE_17
    )
    tmtc_backend.start = MagicMock(return_value=0)
    tmtc_backend.initialize = MagicMock(return_value=0)
    return tmtc_backend


def create_frontend_mock() -> FrontendBase:
    from tmtccmd.core.frontend_base import FrontendBase
    tmtc_frontend = FrontendBase()
    tmtc_frontend.start = MagicMock(return_value=0)
    return tmtc_frontend
