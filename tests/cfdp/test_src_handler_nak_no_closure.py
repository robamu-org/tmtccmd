import random
from crcmod.predefined import PredefinedCrc

from spacepackets.util import ByteFieldU16, ByteFieldU8
from tmtccmd.cfdp.defs import CfdpStates, SourceTransactionStep
from tmtccmd.cfdp.handler import SourceHandler, FsmResult
from tmtccmd.cfdp.request import PutRequest, PutRequestCfg
from .test_src_handler import TestCfdpSourceHandler


class TestCfdpSourceHandlerNoClosure(TestCfdpSourceHandler):
    def setUp(self) -> None:
        self.common_setup(False)

    def test_empty_file(self):
        self._common_empty_file_test()

    def test_small_file(self):
        self._common_small_file_test()
        self._test_transaction_completion(self.source_handler)

    def test_perfectly_segmented_file(self):
        # This tests generates two file data PDUs
        rand_data = random.randbytes(self.file_segment_len * 2)
        self.source_id = ByteFieldU8(1)
        self.dest_id = ByteFieldU8(2)
        self.source_handler.source_id = self.source_id
        dest_path = "/tmp/hello_two_segments_copy.txt"
        file_size, crc32 = self._transaction_with_file_data_wrapper(
            dest_path, rand_data
        )
        self._first_file_segment_handling(self.source_handler, rand_data)
        file_data_pdu = self._second_file_segment_handling(self.source_handler)
        self.assertEqual(len(file_data_pdu.file_data), self.file_segment_len)
        self.assertEqual(
            file_data_pdu.file_data[0 : self.file_segment_len],
            rand_data[self.file_segment_len :],
        )
        self.assertEqual(file_data_pdu.offset, self.file_segment_len)
        self.source_handler.confirm_packet_sent_advance_fsm()
        fsm_res = self.source_handler.state_machine()
        self._test_eof_file_pdu(fsm_res, file_size, crc32)
        self._test_transaction_completion(self.source_handler)

    def test_segmented_file(self):
        # This tests generates two file data PDUs, but the second one does not have a
        # full segment length
        rand_data = random.randbytes(round(self.file_segment_len * 1.5))
        remainder_len = len(rand_data) - self.file_segment_len
        self.source_id = ByteFieldU16(1)
        self.dest_id = ByteFieldU16(2)
        self.source_handler.source_id = self.source_id
        dest_path = "/tmp/hello_two_segments_imperfect_copy.txt"
        file_size, crc32 = self._transaction_with_file_data_wrapper(
            dest_path, rand_data
        )
        self._first_file_segment_handling(self.source_handler, rand_data)
        file_data_pdu = self._second_file_segment_handling(self.source_handler)
        self.assertEqual(len(file_data_pdu.file_data), remainder_len)
        self.assertEqual(
            file_data_pdu.file_data[:],
            rand_data[self.file_segment_len :],
        )
        self.assertEqual(file_data_pdu.offset, self.file_segment_len)
        self.source_handler.confirm_packet_sent_advance_fsm()
        fsm_res = self.source_handler.state_machine()
        self._test_eof_file_pdu(fsm_res, file_size, crc32)
        self._test_transaction_completion(self.source_handler)

    def _second_file_segment_handling(self, source_handler: SourceHandler):
        source_handler.confirm_packet_sent_advance_fsm()
        fsm_res = source_handler.state_machine()
        self.assertEqual(fsm_res.states.state, CfdpStates.BUSY_CLASS_1_NACKED)
        self.assertEqual(fsm_res.states.step, SourceTransactionStep.SENDING_FILE_DATA)
        self.assertFalse(fsm_res.pdu_holder.is_file_directive)
        return fsm_res.pdu_holder.to_file_data_pdu()

    def _transaction_with_file_data_wrapper(
        self, dest_path: str, data: bytes
    ) -> (int, bytes):
        put_req_cfg = PutRequestCfg(
            destination_id=self.dest_id,
            source_file=self.file_path,
            dest_file=dest_path,
            # Let the transmission mode be auto-determined by the remote MIB
            trans_mode=None,
            closure_requested=False,
        )
        with open(self.file_path, "wb") as of:
            crc32 = PredefinedCrc("crc32")
            crc32.update(data)
            crc32 = crc32.digest()
            of.write(data)
        file_size = self.file_path.stat().st_size
        self.local_cfg.local_entity_id = self.source_id
        self._start_source_transaction(self.dest_id, PutRequest(put_req_cfg))
        return file_size, crc32

    def _first_file_segment_handling(self, source_handler: SourceHandler, data: bytes):
        fsm_res = source_handler.state_machine()
        file_data_pdu = self._check_file_data(fsm_res)
        self.assertEqual(len(file_data_pdu.file_data), self.file_segment_len)
        self.assertEqual(
            file_data_pdu.file_data[0 : self.file_segment_len],
            data[0 : self.file_segment_len],
        )
        self.assertEqual(file_data_pdu.offset, 0)

    def _test_eof_file_pdu(self, fsm_res: FsmResult, file_size: int, crc32: bytes):
        self.assertEqual(fsm_res.states.state, CfdpStates.BUSY_CLASS_1_NACKED)
        self.assertEqual(fsm_res.states.step, SourceTransactionStep.SENDING_EOF)
        eof_pdu = fsm_res.pdu_holder.to_eof_pdu()
        self.assertEqual(eof_pdu.file_size, file_size)
        self.assertEqual(eof_pdu.file_checksum, crc32)

    def _test_transaction_completion(self, source_handler: SourceHandler):
        source_handler.confirm_packet_sent_advance_fsm()
        self.assertTrue(self.cfdp_user.eof_sent_indication_was_called)
        self.assertEqual(self.cfdp_user.eof_sent_indication_call_count, 1)
        fsm_res = source_handler.state_machine()
        self.assertEqual(fsm_res.states.state, CfdpStates.IDLE)
        self.assertEqual(fsm_res.states.step, SourceTransactionStep.IDLE)
        self.assertTrue(self.cfdp_user.transaction_finished_was_called)
        self.assertEqual(self.cfdp_user.transaction_finished_call_count, 1)
