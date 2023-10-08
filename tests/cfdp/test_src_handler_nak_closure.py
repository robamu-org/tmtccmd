import os
from pathlib import Path
import random
import sys
from unittest.mock import MagicMock

from spacepackets.cfdp import ConditionCode, Direction, DirectiveType
from spacepackets.cfdp.pdu import FinishedPdu, FileDeliveryStatus, DeliveryCode
from spacepackets.cfdp.pdu.finished import FinishedParams
from spacepackets.util import (
    ByteFieldU8,
    UnsignedByteField,
    ByteFieldU16,
    ByteFieldEmpty,
)
from tmtccmd.cfdp.defs import CfdpState
from tmtccmd.cfdp.handler.defs import (
    InvalidPduDirection,
    InvalidSourceId,
    InvalidDestinationId,
)
from tmtccmd.cfdp.handler.source import TransactionStep
from tmtccmd.cfdp.request import PutRequest
from .test_src_handler import TestCfdpSourceHandler


class TestCfdpSourceHandlerWithClosure(TestCfdpSourceHandler):
    def setUp(self) -> None:
        self.common_setup(True)
        self.seq_num_provider.get_and_increment = MagicMock(return_value=2)

    def test_empty_file_pdu_generation(self):
        self._common_empty_file_test()
        self._pass_simple_finish_pdu_to_source_handler()
        # Transaction should be finished
        fsm_res = self.source_handler.state_machine()
        self._state_checker(fsm_res, False, CfdpState.IDLE, TransactionStep.IDLE)

    def test_small_file_pdu_generation(self):
        file_content = "Hello World\n"
        transaction_id = self._common_small_file_test(True, file_content)
        self._verify_eof_indication(transaction_id)
        self.source_handler.state_machine()
        self._pass_simple_finish_pdu_to_source_handler()
        # Transaction should be finished
        fsm_res = self.source_handler.state_machine()
        self._state_checker(fsm_res, False, CfdpState.IDLE, TransactionStep.IDLE)

    def test_invalid_dir_pdu_passed(self):
        dest_id = ByteFieldU16(2)
        self._start_source_transaction(dest_id, self._prepare_dummy_put_req(dest_id))
        finish_pdu = self._prepare_finish_pdu()
        finish_pdu.pdu_file_directive.pdu_header.direction = Direction.TOWARDS_RECEIVER
        with self.assertRaises(InvalidPduDirection):
            self.source_handler.insert_packet(finish_pdu)

    def test_cancelled_transaction(self):
        # This tests generates two file data PDUs
        if sys.version_info >= (3, 9):
            rand_data = random.randbytes(self.file_segment_len * 2)
        else:
            rand_data = os.urandom(self.file_segment_len * 2)
        self.source_id = ByteFieldU8(1)
        self.dest_id = ByteFieldU8(2)
        self.source_handler.source_id = self.source_id
        dest_path = Path("/tmp/hello_two_segments_copy.txt")
        # The calculated CRC in the EOF (Cancel) PDU will only be calculated for the first segment
        transaction_id, file_size, crc32 = self._transaction_with_file_data_wrapper(
            dest_path, rand_data[0 : self.file_segment_len]
        )
        self._first_file_segment_handling(self.source_handler, rand_data)
        self.assertTrue(self.source_handler.cancel_request(transaction_id))
        self.assertEqual(self.source_handler.step, TransactionStep.SENDING_EOF)
        next_packet = self.source_handler.get_next_packet()
        assert next_packet is not None
        self.assertTrue(next_packet.is_file_directive)
        self.assertEqual(next_packet.pdu_directive_type, DirectiveType.EOF_PDU)
        eof_pdu = next_packet.to_eof_pdu()
        self.assertEqual(crc32, eof_pdu.file_checksum)
        self.assertEqual(eof_pdu.file_size, self.file_segment_len)
        self.assertEqual(eof_pdu.file_size, file_size)
        fsm_res = self.source_handler.state_machine()
        self._state_checker(fsm_res, False, CfdpState.IDLE, TransactionStep.IDLE)

    def test_invalid_source_id_pdu_passed(self):
        dest_id = ByteFieldU16(2)
        finish_pdu = self._regular_transaction_start(dest_id)
        finish_pdu.pdu_file_directive.pdu_conf.source_entity_id = ByteFieldEmpty()
        with self.assertRaises(InvalidSourceId) as cm:
            self.source_handler.insert_packet(finish_pdu)
        exception = cm.exception
        self.assertEqual(exception.found_src_id, ByteFieldEmpty())
        self.assertEqual(exception.expected_src_id, ByteFieldU16(1))

    def test_invalid_dest_id_pdu_passed(self):
        dest_id = ByteFieldU16(3)
        finish_pdu = self._regular_transaction_start(dest_id)
        finish_pdu.pdu_file_directive.pdu_conf.dest_entity_id = ByteFieldEmpty()
        with self.assertRaises(InvalidDestinationId) as cm:
            self.source_handler.insert_packet(finish_pdu)
        exception = cm.exception
        self.assertEqual(exception.found_dest_id, ByteFieldEmpty())
        self.assertEqual(exception.expected_dest_id, ByteFieldU16(3))

    def _regular_transaction_start(self, dest_id: UnsignedByteField) -> FinishedPdu:
        self._start_source_transaction(dest_id, self._prepare_dummy_put_req(dest_id))
        finish_pdu = self._prepare_finish_pdu()
        self.assertEqual(finish_pdu.transaction_seq_num.value, 2)
        return finish_pdu

    def _prepare_dummy_put_req(self, dest_id: UnsignedByteField) -> PutRequest:
        return PutRequest(
            destination_id=dest_id,
            source_file=self.file_path,
            dest_file=Path("dummy.txt"),
            # Let the transmission mode be auto-determined by the remote MIB
            trans_mode=None,
            closure_requested=None,
        )

    def _pass_simple_finish_pdu_to_source_handler(self):
        self._state_checker(
            None,
            False,
            CfdpState.BUSY_CLASS_1_NACKED,
            TransactionStep.WAITING_FOR_FINISHED,
        )
        self.source_handler.insert_packet(self._prepare_finish_pdu())

    def _prepare_finish_pdu(self):
        reply_conf = self.source_handler.pdu_conf
        reply_conf.direction = Direction.TOWARDS_SENDER
        # reply_conf.dest_entity_id = dest_id
        params = FinishedParams(
            delivery_code=DeliveryCode.DATA_COMPLETE,
            condition_code=ConditionCode.NO_ERROR,
            delivery_status=FileDeliveryStatus.FILE_RETAINED,
        )
        return FinishedPdu(
            params=params,
            pdu_conf=reply_conf,
        )
