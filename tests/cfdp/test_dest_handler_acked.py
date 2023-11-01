import struct
from typing import List, Tuple

from spacepackets.cfdp import (
    NULL_CHECKSUM_U32,
    ConditionCode,
    DirectiveType,
    PduType,
    TransmissionMode,
)
from spacepackets.cfdp.pdu import AckPdu, FinishedPdu, TransactionStatus
from spacepackets.crc import mkPredefinedCrcFun

from .test_dest_handler import TestDestHandlerBase
from tmtccmd.cfdp.defs import CfdpState
from tmtccmd.cfdp.handler.dest import FsmResult, TransactionStep


class TestDestHandlerAcked(TestDestHandlerBase):
    def setUp(self) -> None:
        self.common_setup(TransmissionMode.ACKNOWLEDGED)

    def test_acked_empty_transfer(self):
        # Basic acknowledged empty file transfer.
        self._generic_transfer_init(0)
        fsm_res = self._generic_insert_eof_pdu(0, NULL_CHECKSUM_U32)
        self._generic_eof_recv_indication_check(fsm_res)
        self._generic_verify_eof_ack_packet(fsm_res)
        fsm_res = self.dest_handler.state_machine()
        finished_pdu = self._generic_no_error_finished_pdu_check(fsm_res)
        self._generic_verify_transfer_completion(fsm_res, bytes())
        self._generic_insert_finished_pdu_ack(finished_pdu)

    def test_acked_small_file_transfer(self):
        file_content = "Hello World!".encode()
        with open(self.src_file_path, "wb") as of:
            of.write(file_content)
        crc32_func = mkPredefinedCrcFun("crc32")
        crc32 = struct.pack("!I", crc32_func(file_content))
        # Basic acknowledged empty file transfer.
        self._generic_transfer_init(len(file_content))
        self._insert_file_segment(file_content, 0)
        fsm_res = self._generic_insert_eof_pdu(len(file_content), crc32)
        self._generic_eof_recv_indication_check(fsm_res)
        self._generic_verify_eof_ack_packet(fsm_res)
        fsm_res = self.dest_handler.state_machine()
        finished_pdu = self._generic_no_error_finished_pdu_check(fsm_res)
        self._generic_verify_transfer_completion(fsm_res, file_content)
        self._generic_insert_finished_pdu_ack(finished_pdu)

    def test_deferred_missing_file_segment_handling(self):
        file_content = "Hello World!".encode()
        with open(self.src_file_path, "wb") as of:
            of.write(file_content)
        crc32_func = mkPredefinedCrcFun("crc32")
        crc32 = struct.pack("!I", crc32_func(file_content))
        self._generic_transfer_init(len(file_content))
        self._insert_file_segment(file_content[0:5], 0)
        fsm_res = self._generic_insert_eof_pdu(len(file_content), crc32)
        self._generic_eof_recv_indication_check(fsm_res)
        self._generic_verify_eof_ack_packet(fsm_res)
        self.dest_handler.state_machine()
        self._state_checker(
            fsm_res, 1, CfdpState.BUSY, TransactionStep.WAITING_FOR_MISSING_DATA
        )
        self.assertTrue(self.dest_handler.deferred_lost_segment_procedure_active)
        self.assertEqual(self.dest_handler.nak_activity_counter, 0)
        self._generic_verify_missing_segment_requested(
            0, len(file_content), [(5, len(file_content))]
        )
        fsm_res = self._insert_file_segment(
            file_content[5:],
            5,
            expected_packets=1,
            expected_step=TransactionStep.SENDING_FINISHED_PDU,
        )
        finished_pdu = self._generic_no_error_finished_pdu_check(fsm_res)
        self._generic_verify_transfer_completion(fsm_res, file_content)
        self._generic_insert_finished_pdu_ack(finished_pdu)

    def test_immediate_missing_file_seg_handling_0(self):
        file_content = "Hello World!".encode()
        with open(self.src_file_path, "wb") as of:
            of.write(file_content)
        crc32_func = mkPredefinedCrcFun("crc32")
        crc32 = struct.pack("!I", crc32_func(file_content))
        self._generic_transfer_init(len(file_content))
        # A middle segment is missing now, with the expected lost segment tuple to be (3, 6). The
        # lost segment is immediately supplied.
        self._insert_file_segment(file_content[0:3], 0)
        self._insert_file_segment(file_content[6:], 6, 1)
        self._generic_verify_missing_segment_requested(0, len(file_content), [(3, 6)])
        # Insert the missing file content.
        self._insert_file_segment(file_content[3:6], 3)
        # All lost segments were delivered, regular transfer finish.
        fsm_res = self._generic_insert_eof_pdu(len(file_content), crc32)
        self._generic_eof_recv_indication_check(fsm_res)
        self._generic_verify_eof_ack_packet(fsm_res)
        fsm_res = self.dest_handler.state_machine()
        finished_pdu = self._generic_no_error_finished_pdu_check(fsm_res)
        self._generic_verify_transfer_completion(fsm_res, file_content)
        self._generic_insert_finished_pdu_ack(finished_pdu)

    def test_immediate_missing_file_seg_handling_1(self):
        file_content = "Hello World!".encode()
        with open(self.src_file_path, "wb") as of:
            of.write(file_content)
        crc32_func = mkPredefinedCrcFun("crc32")
        crc32 = struct.pack("!I", crc32_func(file_content))
        self._generic_transfer_init(len(file_content))
        # Simulate the second segment being lost, with more than one segment following after that.
        self._insert_file_segment(file_content[0:2], 0)
        self._insert_file_segment(file_content[4:6], 4, 1)
        self._generic_verify_missing_segment_requested(0, 6, [(2, 4)])
        # Insert the last file segment.
        self._insert_file_segment(file_content[6:], 6)
        # Now insert the missing segment.
        self._insert_file_segment(file_content[2:4], 2)
        # All lost segments were delivered, regular transfer finish.
        fsm_res = self._generic_insert_eof_pdu(len(file_content), crc32)
        self._generic_eof_recv_indication_check(fsm_res)
        self._generic_verify_eof_ack_packet(fsm_res)
        fsm_res = self.dest_handler.state_machine()
        finished_pdu = self._generic_no_error_finished_pdu_check(fsm_res)
        self._generic_verify_transfer_completion(fsm_res, file_content)
        self._generic_insert_finished_pdu_ack(finished_pdu)

    def test_immediate_multi_missing_segment_handling(self):
        file_content = "Hello World!".encode()
        with open(self.src_file_path, "wb") as of:
            of.write(file_content)
        crc32_func = mkPredefinedCrcFun("crc32")
        crc32 = struct.pack("!I", crc32_func(file_content))
        self._generic_transfer_init(len(file_content))
        self._insert_file_segment(file_content[0:2], 0)
        self._insert_file_segment(file_content[4:6], 4, 1)
        # First missing segment.
        self._generic_verify_missing_segment_requested(0, 6, [(2, 4)])

        # Second missing segment directly after that.
        self._insert_file_segment(file_content[8:], 8, 1)
        self._generic_verify_missing_segment_requested(0, len(file_content), [(6, 8)])

        # Supply the 2 missing file segments.
        self._insert_file_segment(file_content[2:4], 2)
        self._insert_file_segment(file_content[6:8], 6)
        # All lost segments were delivered, regular transfer finish.
        fsm_res = self._generic_insert_eof_pdu(len(file_content), crc32)
        self._generic_eof_recv_indication_check(fsm_res)
        self._generic_verify_eof_ack_packet(fsm_res)
        fsm_res = self.dest_handler.state_machine()
        finished_pdu = self._generic_no_error_finished_pdu_check(fsm_res)
        self._generic_verify_transfer_completion(fsm_res, file_content)
        self._generic_insert_finished_pdu_ack(finished_pdu)

    def test_immediate_missing_segment_also_rerequested_after_eof(self):
        file_content = "Hello World!".encode()
        with open(self.src_file_path, "wb") as of:
            of.write(file_content)
        crc32_func = mkPredefinedCrcFun("crc32")
        crc32 = struct.pack("!I", crc32_func(file_content))
        self._generic_transfer_init(len(file_content))
        # Missing middle segment
        self._insert_file_segment(file_content[0:2], 0)
        self._insert_file_segment(file_content[6:], 6, 1)
        # Missing segment immediately re-requested.
        self._generic_verify_missing_segment_requested(0, len(file_content), [(2, 6)])

        # All lost segments were delivered, regular transfer finish.
        fsm_res = self._generic_insert_eof_pdu(len(file_content), crc32)
        self._generic_eof_recv_indication_check(fsm_res)
        self._generic_verify_eof_ack_packet(fsm_res)

        self.dest_handler.state_machine()
        self._state_checker(
            fsm_res, 1, CfdpState.BUSY, TransactionStep.WAITING_FOR_MISSING_DATA
        )
        self.assertTrue(self.dest_handler.deferred_lost_segment_procedure_active)
        self.assertEqual(self.dest_handler.nak_activity_counter, 0)
        self._generic_verify_missing_segment_requested(0, len(file_content), [(2, 6)])
        fsm_res = self._insert_file_segment(
            file_content[2:6],
            2,
            1,
            expected_step=TransactionStep.SENDING_FINISHED_PDU,
        )
        finished_pdu = self._generic_no_error_finished_pdu_check(fsm_res)
        self._generic_verify_transfer_completion(fsm_res, file_content)
        self._generic_insert_finished_pdu_ack(finished_pdu)

    def test_multi_segment_missing_deferred_handling(self):
        file_content = "Hello World!".encode()
        with open(self.src_file_path, "wb") as of:
            of.write(file_content)
        crc32_func = mkPredefinedCrcFun("crc32")
        crc32 = struct.pack("!I", crc32_func(file_content))
        self._generic_transfer_init(len(file_content))
        self._insert_file_segment(file_content[0:2], 0)
        self._insert_file_segment(file_content[4:6], 4, 1)
        # First missing segment.
        self._generic_verify_missing_segment_requested(0, 6, [(2, 4)])

        # Second missing segment directly after that.
        self._insert_file_segment(file_content[8:], 8, 1)
        self._generic_verify_missing_segment_requested(0, len(file_content), [(6, 8)])

        fsm_res = self._generic_insert_eof_pdu(len(file_content), crc32)
        self._generic_eof_recv_indication_check(fsm_res)
        self._generic_verify_eof_ack_packet(fsm_res)

        self.dest_handler.state_machine()
        self._state_checker(
            fsm_res, 1, CfdpState.BUSY, TransactionStep.WAITING_FOR_MISSING_DATA
        )
        self.assertTrue(self.dest_handler.deferred_lost_segment_procedure_active)
        self.assertEqual(self.dest_handler.nak_activity_counter, 0)
        # We now receive a NAK sequence with both missing file segments.
        self._generic_verify_missing_segment_requested(
            0, len(file_content), [(2, 4), (6, 8)]
        )
        # We insert both missing file segments.
        fsm_res = self._insert_file_segment(
            file_content[2:4],
            2,
            expected_packets=0,
            expected_step=TransactionStep.WAITING_FOR_MISSING_DATA,
        )
        fsm_res = self._insert_file_segment(
            file_content[6:8],
            6,
            expected_packets=1,
            expected_step=TransactionStep.SENDING_FINISHED_PDU,
        )
        # Done.
        finished_pdu = self._generic_no_error_finished_pdu_check(fsm_res)
        self._generic_verify_transfer_completion(fsm_res, file_content)
        self._generic_insert_finished_pdu_ack(finished_pdu)

    def test_missing_metadata_pdu(self):
        # TODO: Implement
        pass

    def test_metadata_eof_only_missing_metadata(self):
        # TODO: Implement
        pass

    def test_deferred_lost_segment_handling_after_timeout(self):
        # TODO: Implement
        pass

    def test_positive_ack_procedure_finished_pdu(self):
        # TODO: Implement
        pass

    def _generic_verify_missing_segment_requested(
        self,
        start_of_scope: int,
        end_of_scope: int,
        segment_reqs: List[Tuple[int, int]],
    ):
        next_pdu = self.dest_handler.get_next_packet()
        assert next_pdu is not None
        self.assertEqual(next_pdu.pdu_type, PduType.FILE_DIRECTIVE)
        self.assertEqual(next_pdu.pdu_directive_type, DirectiveType.NAK_PDU)
        nak_pdu = next_pdu.to_nak_pdu()
        self.assertEqual(nak_pdu.start_of_scope, 0)
        self.assertEqual(nak_pdu.end_of_scope, end_of_scope)
        self.assertEqual(nak_pdu.segment_requests, segment_reqs)

    def _generic_verify_eof_ack_packet(self, fsm_res: FsmResult):
        self._state_checker(
            fsm_res,
            1,
            CfdpState.BUSY,
            TransactionStep.SENDING_EOF_ACK_PDU,
        )
        next_pdu = self.dest_handler.get_next_packet()
        assert next_pdu is not None
        self.assertEqual(next_pdu.pdu_type, PduType.FILE_DIRECTIVE)
        self.assertEqual(next_pdu.pdu_directive_type, DirectiveType.ACK_PDU)
        ack_pdu = next_pdu.to_ack_pdu()
        self.assertEqual(ack_pdu.directive_code_of_acked_pdu, DirectiveType.EOF_PDU)
        self.assertEqual(ack_pdu.condition_code_of_acked_pdu, ConditionCode.NO_ERROR)
        self.assertEqual(ack_pdu.transaction_status, TransactionStatus.ACTIVE)

    def _generic_insert_finished_pdu_ack(self, finished_pdu: FinishedPdu):
        ack_pdu = AckPdu(
            finished_pdu.pdu_header.pdu_conf,
            DirectiveType.FINISHED_PDU,
            finished_pdu.condition_code,
            TransactionStatus.ACTIVE,
        )
        self.dest_handler.insert_packet(ack_pdu)
        fsm_res = self.dest_handler.state_machine()
        self._state_checker(fsm_res, 0, CfdpState.IDLE, TransactionStep.IDLE)
