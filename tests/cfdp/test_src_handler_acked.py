from pathlib import Path
import sys
import os
import random
import time
from unittest.mock import MagicMock
from crcmod.predefined import PredefinedCrc
from spacepackets.cfdp import (
    NULL_CHECKSUM_U32,
    ConditionCode,
    Direction,
    DirectiveType,
    PduConfig,
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

    def test_empty_file_transfer(self):
        _, _, eof_pdu = self._common_empty_file_test(None)
        self._generic_acked_transfer_completion(eof_pdu)

    def test_small_file_transfer(self):
        _, _, _, eof_pdu = self._common_small_file_test(
            TransmissionMode.ACKNOWLEDGED,
            True,
            "Hello World!",
        )
        self._generic_acked_transfer_completion(eof_pdu)

    def test_missing_metadata_pdu_retransmission(self):
        _, first_metadata_pdu, eof_pdu = self._common_empty_file_test(None)
        # Generate appropriate NAK PDU and insert it.
        nak_missing_metadata = NakPdu(eof_pdu.pdu_header.pdu_conf, 0, 0, [(0, 0)])
        self.source_handler.insert_packet(nak_missing_metadata)
        self.source_handler.state_machine()
        self._state_checker(
            None,
            True,
            CfdpState.BUSY,
            TransactionStep.RETRANSMITTING,
        )
        next_pdu = self.source_handler.get_next_packet()
        assert next_pdu is not None
        self.assertEqual(next_pdu.pdu_type, PduType.FILE_DIRECTIVE)
        self.assertEqual(next_pdu.pdu_directive_type, DirectiveType.METADATA_PDU)
        metadata_pdu = next_pdu.to_metadata_pdu()
        self.assertEqual(metadata_pdu, first_metadata_pdu)
        self.source_handler.state_machine()
        self._generic_acked_transfer_completion(eof_pdu)

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
            CfdpState.BUSY,
            TransactionStep.RETRANSMITTING,
        )
        next_pdu = self.source_handler.get_next_packet()
        assert next_pdu is not None
        self.assertEqual(next_pdu.pdu_type, PduType.FILE_DATA)
        fd_pdu = next_pdu.to_file_data_pdu()
        self.assertEqual(fd_pdu, first_fd_pdu)
        self.source_handler.state_machine()
        self._generic_acked_transfer_completion(eof_pdu)

    def test_positive_ack_procedure(self):
        # 1. Send EOF PDU.
        # 2. Verify EOF PDU is sent again after ACK limit is reached once.
        _, _, initial_eof_pdu = self._common_empty_file_test(None)
        self.assertEqual(self.source_handler.positive_ack_counter, 0)
        # 100 ms timeout, sleep of 150 ms should trigger EOF re-send.
        time.sleep(0.015)
        self._verify_eof_pdu_for_positive_ack(initial_eof_pdu, 1)

    def test_ack_limit_reached(self):
        # This tests fully checks the case where the ACK limit is reached and a corresponding
        # fault is declared.
        transaction_id, _, initial_eof_pdu = self._common_empty_file_test(None)
        self.assertEqual(self.source_handler.positive_ack_counter, 0)
        # 100 ms timeout, sleep of 150 ms should trigger EOF re-send.
        time.sleep(0.015)
        self._verify_eof_pdu_for_positive_ack(initial_eof_pdu, 1)
        time.sleep(0.015)
        self._verify_eof_pdu_for_positive_ack(initial_eof_pdu, 2)
        time.sleep(0.015)
        self.source_handler.state_machine()
        # That's odd but expected. The ACK limit reached fault will trigger a notice
        # of cancellation by default, which causes it to send an EOF PDU with the appropriate
        # condition code. There is little chance that this PDU will arrive after all the
        # others did not arrive in a real use case, but this is standard conformant behaviour.
        # If the the positive ACK procedure fails for this EOF PDU, the standard behaviour
        # is abandonment of the transaction, irrespective of any fault handler configuration,
        # according to section 4.11.2.2.3 of the standard.
        self._state_checker(
            None,
            1,
            CfdpState.BUSY,
            TransactionStep.SENDING_EOF,
        )
        cancelation_cb_mock: MagicMock = self.fault_handler.notice_of_cancellation_cb  # type: ignore
        cancelation_cb_mock.assert_called_once()
        cancelation_cb_mock.assert_called_with(
            transaction_id, ConditionCode.POSITIVE_ACK_LIMIT_REACHED, 0
        )

        next_pdu = self.source_handler.get_next_packet()
        assert next_pdu is not None
        self.assertEqual(next_pdu.pdu_type, PduType.FILE_DIRECTIVE)
        self.assertEqual(next_pdu.pdu_directive_type, DirectiveType.EOF_PDU)
        eof_pdu_for_cancellation = next_pdu.to_eof_pdu()
        self.assertEqual(
            eof_pdu_for_cancellation.condition_code,
            ConditionCode.POSITIVE_ACK_LIMIT_REACHED,
        )
        self.assertEqual(eof_pdu_for_cancellation.file_checksum, NULL_CHECKSUM_U32)
        self.assertEqual(eof_pdu_for_cancellation.file_size, 0)
        # Calling the state machine again confirms we sent or handled the EOF packet,
        # and only then will the positive ACK counter be reset.
        self.source_handler.state_machine()
        self._state_checker(
            None, 0, CfdpState.BUSY, TransactionStep.WAITING_FOR_EOF_ACK
        )
        self.assertEqual(self.source_handler.positive_ack_counter, 0)
        time.sleep(0.015)
        self._verify_eof_pdu_for_positive_ack(eof_pdu_for_cancellation, 1)
        time.sleep(0.015)
        self._verify_eof_pdu_for_positive_ack(eof_pdu_for_cancellation, 2)
        time.sleep(0.015)
        self.source_handler.state_machine()
        self.expected_cfdp_state = CfdpState.IDLE
        # Transaction was abandoned.
        self._state_checker(
            None,
            0,
            CfdpState.IDLE,
            TransactionStep.IDLE,
        )
        abandoned_cb_mock: MagicMock = self.fault_handler.abandoned_cb  # type: ignore
        abandoned_cb_mock.assert_called_once()
        abandoned_cb_mock.assert_called_with(
            transaction_id, ConditionCode.POSITIVE_ACK_LIMIT_REACHED, 0
        )

    def test_ack_procedure_success(self):
        # 1. Send EOF PDU.
        # 2. Verify EOF PDU is sent again after ACK limit is reached once.
        self.assertEqual(self.source_handler.positive_ack_counter, 0)
        transaction_id, _, initial_eof_pdu = self._common_empty_file_test(None)
        # 10 ms timeout, sleep of 15 ms should trigger EOF re-send.
        time.sleep(0.015)
        self._verify_eof_pdu_for_positive_ack(initial_eof_pdu, 1)
        self._generic_acked_transfer_completion(initial_eof_pdu)

    def test_large_missing_chunk_retransmission(self):
        # This tests generates three file data PDUs
        if sys.version_info >= (3, 9):
            rand_data = random.randbytes(self.file_segment_len * 3)
        else:
            rand_data = os.urandom(self.file_segment_len * 3)
        crc32 = PredefinedCrc("crc32")
        crc32.update(rand_data)
        crc32 = crc32.digest()
        dest_path = Path("/tmp/hello_three_segments_copy.txt")
        transaction_params = self._transaction_with_file_data_wrapper(
            dest_path, rand_data
        )
        current_idx = 0
        fd_pdu_list = []
        while current_idx < len(rand_data):
            fd_pdu_list.append(
                self._handle_next_file_data_pdu(
                    current_idx,
                    rand_data[current_idx : current_idx + self.file_segment_len],
                    0,
                )
            )
            current_idx += self.file_segment_len
        eof_pdu = self._handle_eof_pdu(transaction_params.id, crc32, len(rand_data))
        all_missing_filedata = NakPdu(
            pdu_conf=eof_pdu.pdu_header.pdu_conf,
            start_of_scope=0,
            end_of_scope=len(rand_data),
            segment_requests=[(0, len(rand_data))],
        )
        self.source_handler.insert_packet(all_missing_filedata)
        fsm_res = self.source_handler.state_machine()
        self._state_checker(fsm_res, 3, CfdpState.BUSY, TransactionStep.RETRANSMITTING)
        # All file data PDUs should be re-sent now.
        for i in range(3):
            next_pdu = self.source_handler.get_next_packet()
            assert next_pdu is not None
            self.assertEqual(fd_pdu_list[i], next_pdu.pdu)
        next_pdu = self.source_handler.get_next_packet()
        assert next_pdu is None
        self.source_handler.state_machine()
        self._generic_acked_transfer_completion(eof_pdu)

    def _generic_acked_transfer_completion(self, eof_pdu: EofPdu):
        self._state_checker(
            None,
            0,
            CfdpState.BUSY,
            TransactionStep.WAITING_FOR_EOF_ACK,
        )
        pdu_conf = eof_pdu.pdu_header.pdu_conf
        self._insert_eof_ack_packet(eof_pdu)
        self._insert_finished_pdu(pdu_conf)
        self._acknowledge_finished_pdu(pdu_conf)
        self.source_handler.state_machine()
        self.expected_cfdp_state = CfdpState.IDLE
        self._state_checker(
            None,
            False,
            CfdpState.IDLE,
            TransactionStep.IDLE,
        )

    def _insert_finished_pdu(self, pdu_conf: PduConfig):
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
            CfdpState.BUSY,
            TransactionStep.SENDING_ACK_OF_FINISHED,
        )

    def _verify_eof_pdu_for_positive_ack(
        self, expected_eof: EofPdu, expected_ack_counter: int
    ):
        self.source_handler.state_machine()
        self.assertEqual(self.source_handler.packets_ready, True)
        self.assertEqual(self.source_handler.num_packets_ready, 1)
        self.assertEqual(self.source_handler.positive_ack_counter, expected_ack_counter)
        next_pdu = self.source_handler.get_next_packet()
        assert next_pdu is not None
        self.assertEqual(next_pdu.pdu_type, PduType.FILE_DIRECTIVE)
        self.assertEqual(next_pdu.pdu_directive_type, DirectiveType.EOF_PDU)
        eof_pdu = next_pdu.to_eof_pdu()
        self.assertEqual(eof_pdu, expected_eof)

    def _acknowledge_finished_pdu(self, pdu_conf: PduConfig):
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

    def _insert_eof_ack_packet(self, eof_pdu: EofPdu):
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
            CfdpState.BUSY,
            TransactionStep.WAITING_FOR_FINISHED,
        )
