import random
from crcmod.predefined import PredefinedCrc

from spacepackets.cfdp import ConditionCode
from spacepackets.cfdp.defs import ChecksumTypes, NULL_CHECKSUM_U32
from spacepackets.cfdp.pdu import DirectiveType
from spacepackets.cfdp.pdu.file_data import FileDataPdu
from spacepackets.util import ByteFieldU16, ByteFieldU32, UnsignedByteField, ByteFieldU8

from tmtccmd.cfdp.defs import CfdpStates, SourceTransactionStep
from tmtccmd.cfdp.handler import CfdpSourceHandler, FsmResult, PacketSendNotConfirmed
from tmtccmd.cfdp.request import CfdpRequestWrapper, PutRequest, PutRequestCfg
from .test_src_handler import TestCfdpSourceHandler


class TestCfdpSourceHandlerNoClosure(TestCfdpSourceHandler):
    def setUp(self) -> None:
        super().setUp()

    def test_empty_file(self):
        dest_path = "/tmp/hello_copy.txt"
        dest_id = ByteFieldU16(2)
        put_req_cfg = PutRequestCfg(
            destination_id=dest_id,
            source_file=self.file_path,
            dest_file=dest_path,
            # Let the transmission mode be auto-determined by the remote MIB
            trans_mode=None,
            closure_requested=False,
        )
        source_handler = self._start_source_transaction(
            dest_id, PutRequest(put_req_cfg)
        )
        fsm_res = source_handler.state_machine()
        self.assertEqual(fsm_res.states.state, CfdpStates.BUSY_CLASS_1_NACKED)
        self.assertEqual(fsm_res.states.step, SourceTransactionStep.SENDING_EOF)
        self.assertTrue(fsm_res.pdu_holder.is_file_directive)
        self.assertEqual(fsm_res.pdu_holder.pdu_directive_type, DirectiveType.EOF_PDU)
        eof_pdu = fsm_res.pdu_holder.to_eof_pdu()
        self.assertEqual(eof_pdu.file_checksum, NULL_CHECKSUM_U32)
        self.assertEqual(eof_pdu.file_size, 0)
        self.assertEqual(eof_pdu.condition_code, ConditionCode.NO_ERROR)
        self.assertEqual(eof_pdu.fault_location, None)
        # This indication will be called if the EOF send was confirmed
        self.assertFalse(self.cfdp_user.eof_sent_indication_was_called)
        source_handler.confirm_packet_sent_advance_fsm()
        self.assertTrue(self.cfdp_user.eof_sent_indication_was_called)
        self.assertEqual(self.cfdp_user.eof_sent_indication_call_count, 1)
        fsm_res = source_handler.state_machine()
        self.assertTrue(self.cfdp_user.transaction_finished_was_called)
        self.assertEqual(self.cfdp_user.transaction_finished_call_count, 1)
        source_handler.confirm_packet_sent_advance_fsm()
        self.assertEqual(fsm_res.states.state, CfdpStates.IDLE)
        self.assertEqual(fsm_res.states.step, SourceTransactionStep.IDLE)

    def test_small_file(self):
        dest_path = "/tmp/hello_copy.txt"
        self.source_id = ByteFieldU32(1)
        self.dest_id = ByteFieldU32(2)
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
            data = "Hello World\n".encode()
            crc32.update(data)
            crc32 = crc32.digest()
            of.write(data)
        file_size = self.file_path.stat().st_size
        self.local_cfg.local_entity_id = self.source_id
        source_handler = self._start_source_transaction(
            self.dest_id, PutRequest(put_req_cfg)
        )
        fsm_res = source_handler.state_machine()
        file_data_pdu = self._check_file_data(fsm_res)
        self.assertFalse(file_data_pdu.has_segment_metadata)
        self.assertEqual(file_data_pdu.file_data, "Hello World\n".encode())
        self.assertEqual(file_data_pdu.offset, 0)
        source_handler.confirm_packet_sent_advance_fsm()
        fsm_res = source_handler.state_machine()
        self.assertEqual(fsm_res.states.state, CfdpStates.BUSY_CLASS_1_NACKED)
        self.assertEqual(fsm_res.states.step, SourceTransactionStep.SENDING_EOF)
        self.assertEqual(fsm_res.pdu_holder.pdu_directive_type, DirectiveType.EOF_PDU)
        eof_pdu = fsm_res.pdu_holder.to_eof_pdu()
        self.assertEqual(crc32, eof_pdu.file_checksum)
        self.assertEqual(eof_pdu.file_size, file_size)
        self.assertEqual(eof_pdu.condition_code, ConditionCode.NO_ERROR)
        with self.assertRaises(PacketSendNotConfirmed):
            source_handler.state_machine()
        self._test_transaction_completion(source_handler)

    def test_perfectly_segmented_file(self):
        # This tests generates two file data PDUs
        rand_data = random.randbytes(self.file_segment_len * 2)
        self.source_id = ByteFieldU8(1)
        self.dest_id = ByteFieldU8(2)
        dest_path = "/tmp/hello_two_segments_copy.txt"
        file_size, crc32, source_handler = self._transaction_with_file_data_wrapper(
            dest_path, rand_data
        )
        self._first_file_segment_handling(source_handler, rand_data)
        file_data_pdu = self._second_file_segment_handling(source_handler)
        self.assertEqual(len(file_data_pdu.file_data), self.file_segment_len)
        self.assertEqual(
            file_data_pdu.file_data[0 : self.file_segment_len],
            rand_data[self.file_segment_len :],
        )
        self.assertEqual(file_data_pdu.offset, self.file_segment_len)
        source_handler.confirm_packet_sent_advance_fsm()
        fsm_res = source_handler.state_machine()
        self._test_eof_file_pdu(fsm_res, file_size, crc32)
        self._test_transaction_completion(source_handler)

    def test_segmented_file(self):
        # This tests generates two file data PDUs, but the second one does not have a
        # full segment length
        rand_data = random.randbytes(round(self.file_segment_len * 1.5))
        remainder_len = len(rand_data) - self.file_segment_len
        self.source_id = ByteFieldU16(1)
        self.dest_id = ByteFieldU16(2)
        dest_path = "/tmp/hello_two_segments_imperfect_copy.txt"
        file_size, crc32, source_handler = self._transaction_with_file_data_wrapper(
            dest_path, rand_data
        )
        self._first_file_segment_handling(source_handler, rand_data)
        file_data_pdu = self._second_file_segment_handling(source_handler)
        self.assertEqual(len(file_data_pdu.file_data), remainder_len)
        self.assertEqual(
            file_data_pdu.file_data[:],
            rand_data[self.file_segment_len :],
        )
        self.assertEqual(file_data_pdu.offset, self.file_segment_len)
        source_handler.confirm_packet_sent_advance_fsm()
        fsm_res = source_handler.state_machine()
        self._test_eof_file_pdu(fsm_res, file_size, crc32)
        self._test_transaction_completion(source_handler)

    def _check_file_data(self, fsm_res: FsmResult) -> FileDataPdu:
        self.assertEqual(fsm_res.states.state, CfdpStates.BUSY_CLASS_1_NACKED)
        self.assertEqual(fsm_res.states.step, SourceTransactionStep.SENDING_FILE_DATA)
        self.assertFalse(fsm_res.pdu_holder.is_file_directive)
        return fsm_res.pdu_holder.to_file_data_pdu()

    def _second_file_segment_handling(self, source_handler: CfdpSourceHandler):
        source_handler.confirm_packet_sent_advance_fsm()
        fsm_res = source_handler.state_machine()
        self.assertEqual(fsm_res.states.state, CfdpStates.BUSY_CLASS_1_NACKED)
        self.assertEqual(fsm_res.states.step, SourceTransactionStep.SENDING_FILE_DATA)
        self.assertFalse(fsm_res.pdu_holder.is_file_directive)
        return fsm_res.pdu_holder.to_file_data_pdu()

    def _transaction_with_file_data_wrapper(
        self, dest_path: str, data: bytes
    ) -> (int, bytes, CfdpSourceHandler):
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
        source_handler = self._start_source_transaction(
            self.dest_id, PutRequest(put_req_cfg)
        )
        return file_size, crc32, source_handler

    def _first_file_segment_handling(
        self, source_handler: CfdpSourceHandler, data: bytes
    ):
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

    def _test_transaction_completion(self, source_handler: CfdpSourceHandler):
        source_handler.confirm_packet_sent_advance_fsm()
        self.assertTrue(self.cfdp_user.eof_sent_indication_was_called)
        self.assertEqual(self.cfdp_user.eof_sent_indication_call_count, 1)
        fsm_res = source_handler.state_machine()
        self.assertEqual(fsm_res.states.state, CfdpStates.IDLE)
        self.assertEqual(fsm_res.states.step, SourceTransactionStep.IDLE)
        self.assertTrue(self.cfdp_user.transaction_finished_was_called)
        self.assertEqual(self.cfdp_user.transaction_finished_call_count, 1)

    def _start_source_transaction(
        self, dest_id: UnsignedByteField, put_request: PutRequest
    ) -> CfdpSourceHandler:
        # Create an empty file and send it via CFDP
        source_handler = CfdpSourceHandler(
            self.local_cfg, self.seq_num_provider, self.cfdp_user
        )

        wrapper = CfdpRequestWrapper(put_request)
        source_handler.start_transaction(wrapper, self.remote_cfg)
        fsm_res = source_handler.state_machine()
        self.assertEqual(fsm_res.states.state, CfdpStates.BUSY_CLASS_1_NACKED)
        self.assertEqual(fsm_res.states.step, SourceTransactionStep.SENDING_METADATA)
        self.assertTrue(self.cfdp_user.transaction_inidcation_was_called)
        self.assertEqual(self.cfdp_user.transaction_inidcation_call_count, 1)
        self.assertTrue(fsm_res.pdu_holder.is_file_directive)
        self.assertEqual(
            fsm_res.pdu_holder.pdu_directive_type, DirectiveType.METADATA_PDU
        )
        metadata_pdu = fsm_res.pdu_holder.to_metadata_pdu()
        if put_request.cfg.closure_requested is not None:
            self.assertEqual(
                metadata_pdu.params.closure_requested, put_request.cfg.closure_requested
            )
        self.assertEqual(metadata_pdu.checksum_type, ChecksumTypes.CRC_32)
        self.assertEqual(metadata_pdu.source_file_name, self.file_path.as_posix())
        self.assertEqual(metadata_pdu.dest_file_name, put_request.cfg.dest_file)
        self.assertEqual(metadata_pdu.dest_entity_id, dest_id)
        source_handler.confirm_packet_sent_advance_fsm()
        return source_handler
