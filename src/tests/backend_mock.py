from unittest.mock import MagicMock
from tmtccmd.core.backend import TmTcHandler
from tmtccmd.core.definitions import CoreComInterfaces, CoreModeList, CoreServiceList


def create_backend_mock() -> TmTcHandler:
    tmtc_backend = TmTcHandler(
        init_com_if=CoreComInterfaces.DUMMY, init_mode=CoreModeList.IDLE,
        init_service=CoreServiceList.SERVICE_17
    )
    tmtc_backend.start = MagicMock(return_value=0)
    tmtc_backend.initialize = MagicMock(return_value=0)
    return tmtc_backend