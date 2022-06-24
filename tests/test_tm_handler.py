from unittest import TestCase

from tmtccmd.ccsds.handler import ApidTmHandlerBase


class TmHandler(ApidTmHandlerBase):
    def __init__(self):
        super().__init__()
        self.was_called = False

    def handle_tm_for_apid(self, apid: int, packet: bytes, user_args: any):
        self.was_called = True


class TestTmHandler(TestCase):
    def test_basic(self):
        tm_handler = TmHandler()
