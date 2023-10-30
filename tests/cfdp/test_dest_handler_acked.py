import struct
from spacepackets.cfdp import (
    NULL_CHECKSUM_U32,
    ConditionCode,
    DirectiveType,
    PduType,
    TransmissionMode,
)
from spacepackets.cfdp.pdu import AckPdu, FinishedPdu, TransactionStatus
from spacepackets.crc import mkPredefinedCrcFun
from tmtccmd.cfdp.defs import CfdpState

from tmtccmd.cfdp.handler.dest import FsmResult, TransactionStep

from .test_dest_handler import TestDestHandlerBase


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

    def test_missing_file_segment_is_rerequested(self):
        file_content = "Hello World!".encode()
        with open(self.src_file_path, "wb") as of:
            of.write(file_content)
        crc32_func = mkPredefinedCrcFun("crc32")
        crc32 = struct.pack("!I", crc32_func(file_content))
        # Basic acknowledged empty file transfer.
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
        self.assertEqual(self.dest_handler.nak_activity_counter, 1)
        next_pdu = self.dest_handler.get_next_packet()
        assert next_pdu is not None
        # finished_pdu = self._generic_no_error_finished_pdu_check(fsm_res)
        # self._generic_verify_transfer_completion(fsm_res, file_content)
        # self._generic_insert_finished_pdu_ack(finished_pdu)

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
