from unittest import TestCase
from tmtccmd.runner import run_tmtc_commander, initialize_tmtc_commander
from backend_mock import create_backend_mock


class TestTmtcRunner(TestCase):
    def test_tmtc_runner(self):
        backend_mock = create_backend_mock()
