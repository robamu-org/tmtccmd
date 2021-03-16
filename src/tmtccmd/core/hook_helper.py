import sys
from tmtccmd.core.hook_base import TmTcHookBase
from tmtccmd.utility.tmtcc_logger import get_logger

LOGGER = get_logger()


def get_global_hook_obj() -> TmTcHookBase:
    try:
        from tmtccmd.core.globals_manager import get_global
        from tmtccmd.core.definitions import CoreGlobalIds

        from typing import cast
        hook_obj_raw = get_global(CoreGlobalIds.TMTC_HOOK)
        if hook_obj_raw is None:
            LOGGER.error("Hook object is invalid!")
            sys.exit(0)
        return cast(TmTcHookBase, hook_obj_raw)
    except ImportError:
        LOGGER.exception("Issues importing modules to get global hook handle!")
    except AttributeError:
        LOGGER.exception("Attribute error when trying to get global hook handle!")

