from spacepackets.cfdp import (
    ConditionCode,
    Direction,
    DirectiveType,
    PduType,
    TransmissionMode,
)
from spacepackets.cfdp.pdu import (
    AckPdu,
    DeliveryCode,
    FileDeliveryStatus,
    FinishedPdu,
    TransactionStatus,
)
from spacepackets.cfdp.pdu.finished import FinishedParams

from tmtccmd.cfdp.defs import CfdpState
from tmtccmd.cfdp.handler.source import TransactionStep
from .test_src_handler import TestCfdpSourceHandler


class TestSourceHandlerAcked(TestCfdpSourceHandler):
    def setUp(self) -> None:
        self.common_setup(True, TransmissionMode.ACKNOWLEDGED)

    def test_empty_file_transfer(self):
        eof_pdu = self._common_empty_file_test(None, CfdpState.BUSY_CLASS_2_ACKED)
        self._state_checker(
            None,
            False,
            CfdpState.BUSY_CLASS_2_ACKED,
            TransactionStep.WAITING_FOR_EOF_ACK,
        )
        # TODO: 1: Acknowledge EOF PDU by inserting ACK, 2: Insert Finished PDU, 3: Retrieve
        # and check ACK PDU generated as a response to the Finished PDU.
        # pdu_conf = PduConfig(eof_pdu.source_entity_id, eof_pdu.dest_entity_id, eof_pdu.transaction_seq_num, eof_pdu.transmission_mode)
        pdu_conf = eof_pdu.pdu_header.pdu_conf
        ack_pdu = AckPdu(
            pdu_conf,
            DirectiveType.EOF_PDU,
            ConditionCode.NO_ERROR,
            TransactionStatus.ACTIVE,
        )
        self.assertEqual(ack_pdu.direction, Direction.TOWARDS_SENDER)
        self.source_handler.insert_packet(ack_pdu)
        self.source_handler.state_machine()
        self._state_checker(
            None,
            False,
            CfdpState.BUSY_CLASS_2_ACKED,
            TransactionStep.WAITING_FOR_FINISHED,
        )
        finished_pdu = FinishedPdu(
            pdu_conf,
            FinishedParams(
                DeliveryCode.DATA_COMPLETE,
                FileDeliveryStatus.FILE_RETAINED,
                ConditionCode.NO_ERROR,
            ),
        )
        self.source_handler.insert_packet(finished_pdu)
        self.source_handler.state_machine()
        self._state_checker(
            None,
            True,
            CfdpState.BUSY_CLASS_2_ACKED,
            TransactionStep.SENDING_ACK_OF_FINISHED,
        )
        next_pdu = self.source_handler.get_next_packet()
        assert next_pdu is not None
        self.assertEqual(next_pdu.pdu_type, PduType.FILE_DIRECTIVE)
        self.assertEqual(next_pdu.pdu_directive_type, DirectiveType.ACK_PDU)
        ack_pdu = next_pdu.to_ack_pdu()
        self.assertEqual(ack_pdu.direction, Direction.TOWARDS_RECEIVER)
        self.assertEqual(
            ack_pdu.directive_code_of_acked_pdu, DirectiveType.FINISHED_PDU
        )
        self.assertEqual(ack_pdu.transaction_status, TransactionStatus.ACTIVE)
        # Set this correctly for test explicitely. Every other field should be the same.
        pdu_conf.direction = Direction.TOWARDS_RECEIVER
        self.assertEqual(ack_pdu.pdu_header.pdu_conf, pdu_conf)
        self.source_handler.state_machine()
        self._state_checker(
            None,
            False,
            CfdpState.IDLE,
            TransactionStep.IDLE,
        )
