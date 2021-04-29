from unittest import TestCase
from tmtccmd.runner import run_tmtc_commander, initialize_tmtc_commander
from tests.backend_mock import create_backend_mock, create_hook_mock, create_frontend_mock


class TestTmtcRunner(TestCase):
    def test_tmtc_runner(self):
        hook_base = create_hook_mock()
        backend_mock = create_backend_mock()
        initialize_tmtc_commander(hook_object=hook_base)
        run_tmtc_commander(False, False, True, tmtc_backend=backend_mock)
        backend_mock.start.assert_called_with()
        backend_mock.initialize.assert_called_with()

        frontend_mock = create_frontend_mock()
        run_tmtc_commander(
            True, False, True, tmtc_backend=backend_mock, tmtc_frontend=frontend_mock
        )
        frontend_mock.start.assert_called_once()
        qt_app = frontend_mock.start.call_args[0][0]
        self.assertTrue(qt_app is not None)

    def test_errors(self):
        self.assertRaises(
            ValueError, initialize_tmtc_commander, None
        )
        self.assertRaises(
            TypeError, run_tmtc_commander
        )
        self.assertRaises(
            ValueError, run_tmtc_commander, False
        )
