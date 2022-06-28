from datetime import timedelta
from unittest import TestCase
from unittest.mock import MagicMock

from tmtccmd import CcsdsTmtcBackend, CcsdsTmListener, TcHandlerBase
from tmtccmd.com_if.dummy import DummyComIF
from tmtccmd.core import TcMode, TmMode, BackendRequest, BackendController
from tmtccmd.tc.ccsds_seq_sender import SenderMode


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
        ctrl = BackendController()
        self.assertEqual(backend.tm_mode, TmMode.IDLE)
        self.assertEqual(backend.tc_mode, TcMode.IDLE)
        self.assertEqual(backend.com_if.get_id(), "dummy")
        self.assertEqual(backend.com_if_id, "dummy")
        self.assertEqual(backend.inter_cmd_delay, timedelta())
        state = backend.state
        self.assertEqual(state.tc_mode, TcMode.IDLE)
        self.assertEqual(state.tm_mode, TmMode.IDLE)
        self.assertEqual(state.next_delay, timedelta())
        self.assertEqual(state.request, BackendRequest.NONE)
        backend.mode_to_req()
        self.assertEqual(state.request, BackendRequest.DELAY_IDLE)
        self.assertEqual(backend.inter_cmd_delay, timedelta())
        self.assertFalse(backend.com_if_active())
        self.assertFalse(com_if.is_open())
        backend.start()
        self.assertTrue(com_if.is_open())
        self.assertTrue(backend.com_if_active())

        res = backend.periodic_op(ctrl)
        self.assertEqual(res.request, BackendRequest.DELAY_IDLE)
        backend.tm_mode = TmMode.LISTENER
        self.assertEqual(backend.tm_mode, TmMode.LISTENER)
        res = backend.periodic_op(ctrl)
        tm_listener.operation.assert_called_once()
        backend.poll_tm()
        self.assertEqual(tm_listener.operation.call_count, 2)
        self.assertEqual(res.request, BackendRequest.DELAY_LISTENER)
        backend.tm_mode = TmMode.IDLE
        backend.tc_mode = TcMode.ONE_QUEUE
        # Our mock does not return a queue, so this operation is done immediately
        res = backend.periodic_op(ctrl)
        self.assertEqual(res.request, BackendRequest.TERMINATION_NO_ERROR)
        self.assertEqual(res.sender_res.mode, SenderMode.DONE)
