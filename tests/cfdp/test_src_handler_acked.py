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
    EofPdu,
    FileDeliveryStatus,
    FinishedPdu,
    NakPdu,
    TransactionStatus,
)
from spacepackets.cfdp.pdu.finished import FinishedParams

from tmtccmd.cfdp.defs import CfdpState
from tmtccmd.cfdp.handler.source import TransactionStep
from .test_src_handler import TestCfdpSourceHandler


class TestSourceHandlerAcked(TestCfdpSourceHandler):
    def setUp(self) -> None:
        self.common_setup(True, TransmissionMode.ACKNOWLEDGED)
        self.expected_cfdp_state = CfdpState.BUSY_CLASS_2_ACKED

    def _generic_success_ack_handling(self, eof_pdu: EofPdu):
        self._state_checker(
            None,
            False,
            TransactionStep.WAITING_FOR_EOF_ACK,
        )
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
        self.expected_cfdp_state = CfdpState.IDLE
        self._state_checker(
            None,
            False,
            TransactionStep.IDLE,
        )

    def test_empty_file_transfer(self):
        _, eof_pdu = self._common_empty_file_test(None)
        self._generic_success_ack_handling(eof_pdu)

    def test_small_file_transfer(self):
        _, _, _, eof_pdu = self._common_small_file_test(
            TransmissionMode.ACKNOWLEDGED,
            True,
            "Hello World!",
        )
        self._generic_success_ack_handling(eof_pdu)

    def test_missing_metadata_pdu_retransmission(self):
        first_metadata_pdu, eof_pdu = self._common_empty_file_test(None)
        # Generate appropriate NAK PDU and insert it.
        nak_missing_metadata = NakPdu(eof_pdu.pdu_header.pdu_conf, 0, 0, [(0, 0)])
        self.source_handler.insert_packet(nak_missing_metadata)
        self.source_handler.state_machine()
        self._state_checker(
            None,
            True,
            TransactionStep.RETRANSMITTING,
        )
        next_pdu = self.source_handler.get_next_packet()
        assert next_pdu is not None
        self.assertEqual(next_pdu.pdu_type, PduType.FILE_DIRECTIVE)
        self.assertEqual(next_pdu.pdu_directive_type, DirectiveType.METADATA_PDU)
        metadata_pdu = next_pdu.to_metadata_pdu()
        self.assertEqual(metadata_pdu, first_metadata_pdu)

    def test_missing_filedata_pdu_retransmission(self):
        file_content = "Hello World!"
        _, _, first_fd_pdu, eof_pdu = self._common_small_file_test(
            TransmissionMode.ACKNOWLEDGED, True, file_content
        )
        end_of_scope = len(file_content.encode())
        # Generate appropriate NAK PDU and insert it.
        nak_missing_metadata = NakPdu(
            eof_pdu.pdu_header.pdu_conf, 0, end_of_scope, [(0, end_of_scope)]
        )
        self.source_handler.insert_packet(nak_missing_metadata)
        self.source_handler.state_machine()
        self._state_checker(
            None,
            True,
            TransactionStep.RETRANSMITTING,
        )
        next_pdu = self.source_handler.get_next_packet()
        assert next_pdu is not None
        self.assertEqual(next_pdu.pdu_type, PduType.FILE_DATA)
        fd_pdu = next_pdu.to_file_data_pdu()
        self.assertEqual(fd_pdu, first_fd_pdu)

    def test_positive_ack_limit_reached(self):
        # TODO: Implement.
        # 1. Trigger a re-send of a file data PDU.
        # 2. Trigger a Positive ACK limit reached procedure.
        # 3. Verify it does ???.
        pass
