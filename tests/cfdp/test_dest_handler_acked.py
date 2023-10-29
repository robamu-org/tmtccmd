from spacepackets.cfdp import (
    NULL_CHECKSUM_U32,
    ConditionCode,
    DirectiveType,
    PduType,
    TransmissionMode,
)
from spacepackets.cfdp.pdu import TransactionStatus

from .test_dest_handler import TestDestHandlerBase


class TestDestHandlerAcked(TestDestHandlerBase):
    def setUp(self) -> None:
        self.common_setup(TransmissionMode.ACKNOWLEDGED)

    def test_acked_empty_transfer(self):
        # Basic acknowledged empty file transfer.
        self._generic_transfer_init(0)
        fsm_res = self._generic_insert_eof_pdu(0, NULL_CHECKSUM_U32)
        self._generic_eof_recv_indication_check(fsm_res)
        next_pdu = self.dest_handler.get_next_packet()
        assert next_pdu is not None
        self.assertEqual(next_pdu.pdu_type, PduType.FILE_DIRECTIVE)
        self.assertEqual(next_pdu.pdu_directive_type, DirectiveType.ACK_PDU)
        ack_pdu = next_pdu.to_ack_pdu()
        self.assertEqual(ack_pdu.directive_code_of_acked_pdu, DirectiveType.EOF_PDU)
        self.assertEqual(ack_pdu.condition_code_of_acked_pdu, ConditionCode.NO_ERROR)
        self.assertEqual(ack_pdu.transaction_status, TransactionStatus.ACTIVE)
        fsm_res = self.dest_handler.state_machine()
        finished_pdu = self._generic_no_error_finished_pdu_check(fsm_res)
        self._generic_verify_transfer_completion(fsm_res, 0)
        # TODO: Send back ACK PDU, verify complete completion.
