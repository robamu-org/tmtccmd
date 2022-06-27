from unittest import TestCase
from unittest.mock import MagicMock

from tmtccmd import CcsdsTmtcBackend, CcsdsTmListener, TcHandlerBase
from tmtccmd.com_if.dummy import DummyComIF
from tmtccmd.core import TcMode, TmMode, BackendRequest


class TestCore(TestCase):
    def test_backend(self):
        com_if = DummyComIF()
        tm_listener = MagicMock(specs=CcsdsTmListener)
        tc_handler = MagicMock(specs=TcHandlerBase)
        backend = CcsdsTmtcBackend(
            tc_mode=TcMode.IDLE,
            tm_mode=TmMode.IDLE,
            com_if=com_if,
            tm_listener=tm_listener,
            tc_handler=tc_handler,
        )
        self.assertEqual(backend.tm_mode, TmMode.IDLE)
        self.assertEqual(backend.tc_mode, TcMode.IDLE)
        self.assertEqual(backend.com_if.get_id(), "dummy")
        self.assertEqual(backend.com_if_id, "dummy")
        self.assertEqual(backend.inter_cmd_delay, 0.0)
        state = backend.state
        self.assertEqual(state.tc_mode, TcMode.IDLE)
        self.assertEqual(state.tm_mode, TmMode.IDLE)
        self.assertEqual(state.next_delay, 0.0)
        self.assertEqual(state.request, BackendRequest.NONE)
        backend.mode_to_req()
        self.assertEqual(state.request, BackendRequest.DELAY_IDLE)
        pass
