from unittest import TestCase
from backend_mock import create_backend_mock


class TestTmtcRunner(TestCase):
    def test_tmtc_runner(self):
        backend_mock = create_backend_mock()
