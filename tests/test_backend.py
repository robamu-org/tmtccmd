from datetime import timedelta
from typing import Optional
from unittest import TestCase
from unittest.mock import MagicMock

from spacepackets.ecss import PusTelecommand
from tmtccmd import CcsdsTmtcBackend, CcsdsTmListener, TcHandlerBase
from tmtccmd.com_if import ComInterface
from tmtccmd.com_if.dummy import DummyComIF
from tmtccmd.core import TcMode, TmMode, BackendRequest, BackendController
from tmtccmd.core.ccsds_backend import NoValidProcedureSet
from tmtccmd.tc import (
    TcProcedureBase,
    DefaultProcedureInfo,
    TcProcedureType,
    ProcedureCastWrapper,
    TcQueueEntryBase,
)
from tmtccmd.tc.ccsds_seq_sender import SenderMode
from tmtccmd.tc.handler import FeedWrapper


class TcHandlerMock(TcHandlerBase):
    def __init__(self):
        super().__init__()
        self.is_feed_cb_valid = False
        self.feed_cb_call_count = 0

    def send_cb(self, tc_queue_entry: TcQueueEntryBase, com_if: ComInterface):
        pass

    def queue_finished_cb(self, info: TcProcedureBase):
        pass

    def feed_cb(self, info: Optional[TcProcedureBase], wrapper: FeedWrapper):
        self.feed_cb_call_count += 1
        cast_wrapper = ProcedureCastWrapper(info)
        if info is not None:
            if info.ptype != TcProcedureType.DEFAULT:
                def_info = cast_wrapper.to_def_procedure()
                if def_info.service != "17":
                    self.is_feed_cb_valid = False
                elif def_info.op_code != "0":
                    self.is_feed_cb_valid = False
            wrapper.queue_helper.add_pus_tc(PusTelecommand(service=17, subservice=1))


class TestBackend(TestCase):
    def test_backend(self):
        com_if = DummyComIF()
        tm_listener = MagicMock(specs=CcsdsTmListener)
        tc_handler = TcHandlerMock()
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

        res = backend.periodic_op()
        self.assertEqual(res.request, BackendRequest.DELAY_IDLE)
        backend.tm_mode = TmMode.LISTENER
        self.assertEqual(backend.tm_mode, TmMode.LISTENER)
        res = backend.periodic_op()
        tm_listener.operation.assert_called_once()
        backend.poll_tm()
        self.assertEqual(tm_listener.operation.call_count, 2)
        self.assertEqual(res.request, BackendRequest.DELAY_LISTENER)
        backend.tm_mode = TmMode.IDLE
        backend.tc_mode = TcMode.ONE_QUEUE
        with self.assertRaises(NoValidProcedureSet):
            backend.periodic_op()
        backend.current_proc_info = DefaultProcedureInfo(service="17", op_code="0")
        res = backend.periodic_op()
        self.assertEqual(res.request, BackendRequest.TERMINATION_NO_ERROR)
