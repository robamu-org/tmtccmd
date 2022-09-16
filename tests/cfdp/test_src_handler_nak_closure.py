from unittest.mock import MagicMock

from spacepackets.cfdp import ConditionCode, Direction
from spacepackets.cfdp.pdu import FinishedPdu, FileDeliveryStatus, DeliveryCode
from spacepackets.cfdp.pdu.finished import FinishedParams
from spacepackets.util import UnsignedByteField, ByteFieldU16, ByteFieldEmpty
from tmtccmd.cfdp.defs import CfdpStates
from tmtccmd.cfdp.handler.defs import (
    InvalidPduDirection,
    InvalidSourceId,
    InvalidDestinationId,
)
from tmtccmd.cfdp.handler.source import TransactionStep
from tmtccmd.cfdp.request import PutRequestCfg, PutRequest
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
        self._state_checker(fsm_res, CfdpStates.IDLE, TransactionStep.IDLE)

    def test_small_file_pdu_generation(self):
        file_content = "Hello World\n"
        self._common_small_file_test(True, file_content)
        self._verify_eof_indication()
        self.source_handler.state_machine()
        self._pass_simple_finish_pdu_to_source_handler()
        # Transaction should be finished
        fsm_res = self.source_handler.state_machine()
        self._state_checker(fsm_res, CfdpStates.IDLE, TransactionStep.IDLE)

    def test_invalid_dir_pdu_passed(self):
        dest_id = ByteFieldU16(2)
        self._start_source_transaction(dest_id, self._prepare_dummy_put_req(dest_id))
        finish_pdu = self._prepare_finish_pdu()
        finish_pdu.pdu_file_directive.pdu_header.direction = Direction.TOWARDS_RECEIVER
        with self.assertRaises(InvalidPduDirection):
            self.source_handler.pass_packet(finish_pdu)

    def test_invalid_source_id_pdu_passed(self):
        dest_id = ByteFieldU16(2)
        finish_pdu = self._regular_transaction_start(dest_id)
        finish_pdu.pdu_file_directive.pdu_conf.source_entity_id = ByteFieldEmpty()
        with self.assertRaises(InvalidSourceId) as cm:
            self.source_handler.pass_packet(finish_pdu)
        exception = cm.exception
        self.assertEqual(exception.found_src_id, ByteFieldEmpty())
        self.assertEqual(exception.expected_src_id, ByteFieldU16(1))

    def test_invalid_dest_id_pdu_passed(self):
        dest_id = ByteFieldU16(3)
        finish_pdu = self._regular_transaction_start(dest_id)
        finish_pdu.pdu_file_directive.pdu_conf.dest_entity_id = ByteFieldEmpty()
        with self.assertRaises(InvalidDestinationId) as cm:
            self.source_handler.pass_packet(finish_pdu)
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
            PutRequestCfg(
                destination_id=dest_id,
                source_file=self.file_path,
                dest_file="dummy.txt",
                # Let the transmission mode be auto-determined by the remote MIB
                trans_mode=None,
                closure_requested=None,
            )
        )

    def _pass_simple_finish_pdu_to_source_handler(self):
        self._state_checker(
            None, CfdpStates.BUSY_CLASS_1_NACKED, TransactionStep.WAIT_FOR_FINISH
        )
        self.source_handler.pass_packet(self._prepare_finish_pdu())

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
