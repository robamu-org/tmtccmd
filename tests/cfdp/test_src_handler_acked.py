from spacepackets.cfdp import TransmissionMode

from tmtccmd.cfdp.defs import CfdpState
from tmtccmd.cfdp.handler.source import TransactionStep
from .test_src_handler import TestCfdpSourceHandler


class TestSourceHandlerAcked(TestCfdpSourceHandler):
    def setUp(self) -> None:
        self.common_setup(True, TransmissionMode.ACKNOWLEDGED)

    def test_empty_file_transfer(self):
        self._common_empty_file_test(None, CfdpState.BUSY_CLASS_2_ACKED)
        self._state_checker(
            None,
            False,
            CfdpState.BUSY_CLASS_2_ACKED,
            TransactionStep.WAITING_FOR_EOF_ACK,
        )
        # TODO: 1: Acknowledge EOF PDU by inserting ACK, 2: Insert Finished PDU, 3: Retrieve
        # and check ACK PDU generated as a response to the Finished PDU.
