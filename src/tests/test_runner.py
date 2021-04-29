from unittest import TestCase
from tmtccmd.runner import run_tmtc_commander, initialize_tmtc_commander
from tests.backend_mock import create_backend_mock, create_hook_mock


class TestTmtcRunner(TestCase):
    def test_tmtc_runner(self):
        hook_base = create_hook_mock()
        backend_mock = create_backend_mock()
        initialize_tmtc_commander(hook_object=hook_base)
        run_tmtc_commander(False, True, False, tmtc_backend=backend_mock)
        backend_mock.start.assert_called_with()
