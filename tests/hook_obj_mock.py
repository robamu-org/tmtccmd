from unittest.mock import MagicMock

from tmtccmd.config import HookBase


def create_hook_mock() -> HookBase:
    """Create simple minimal hook mock using the MagicMock facilities by unittest
    :return:
    """
    tmtc_hook_base = MagicMock(spec=HookBase)
    return tmtc_hook_base
