from spacepackets.cfdp import ConditionCode, Direction
from spacepackets.cfdp.pdu import FinishedPdu, FileDeliveryStatus, DeliveryCode
from spacepackets.cfdp.pdu.finished import FinishedParams
from tmtccmd.cfdp.defs import CfdpStates, SourceTransactionStep
from .test_src_handler import TestCfdpSourceHandler


class TestCfdpSourceHandlerWithClosure(TestCfdpSourceHandler):
    def setUp(self) -> None:
        self.common_setup(True)

    def test_empty_file(self):
        self._common_empty_file_test()
        self.assertEqual(
            self.source_handler.states.state, CfdpStates.BUSY_CLASS_1_NACKED
        )
        self.assertEqual(
            self.source_handler.states.step, SourceTransactionStep.WAIT_FOR_FINISH
        )
        reply_conf = self.source_handler.pdu_conf
        reply_conf.direction = Direction.TOWARDS_SENDER
        params = FinishedParams(
            delivery_code=DeliveryCode.DATA_COMPLETE,
            condition_code=ConditionCode.NO_ERROR,
            delivery_status=FileDeliveryStatus.FILE_RETAINED,
        )
        finish_pdu = FinishedPdu(
            params=params,
            pdu_conf=reply_conf,
        )
        self.source_handler.pass_packet(finish_pdu)
        # Transaction should be finished
        fsm_res = self.source_handler.state_machine()
        self.assertEqual(fsm_res.states.state, CfdpStates.IDLE)
        self.assertEqual(fsm_res.states.step, SourceTransactionStep.IDLE)

    def test_small_file(self):
        pass
