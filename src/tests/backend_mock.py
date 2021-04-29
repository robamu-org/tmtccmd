from unittest.mock import MagicMock
from abc import abstractmethod
from tmtccmd.core.backend import TmTcHandler
from tmtccmd.core.hook_base import TmTcHookBase
from tmtccmd.core.definitions import CoreComInterfaces, CoreModeList, CoreServiceList


def create_hook_mock() -> TmTcHookBase:
    tmtc_hook_base = TmTcHookBase()
    tmtc_hook_base.add_globals_pre_args_parsing = MagicMock(return_value=0)
    tmtc_hook_base.add_globals_post_args_parsing = MagicMock(return_value=0)
    return tmtc_hook_base


def create_backend_mock() -> TmTcHandler:
    tmtc_backend = TmTcHandler(
        init_com_if=CoreComInterfaces.DUMMY, init_mode=CoreModeList.IDLE,
        init_service=CoreServiceList.SERVICE_17
    )
    tmtc_backend.start = MagicMock(return_value=0)
    tmtc_backend.initialize = MagicMock(return_value=0)
    return tmtc_backend
