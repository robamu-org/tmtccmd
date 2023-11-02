from threading import Lock
import dataclasses
import os
import tempfile
from pathlib import Path
from typing import Optional, Tuple, cast
from unittest import TestCase
from unittest.mock import MagicMock

from spacepackets.cfdp import (
    ChecksumType,
    ConditionCode,
    Direction,
    DirectiveType,
    PduConfig,
    PduType,
    TransmissionMode,
)
from spacepackets.cfdp.pdu import (
    DeliveryCode,
    EofPdu,
    FileDataPdu,
    FileDeliveryStatus,
    FinishedPdu,
    MetadataPdu,
)
from spacepackets.cfdp.pdu.file_data import FileDataParams
from spacepackets.cfdp.pdu.metadata import MetadataParams
from spacepackets.util import ByteFieldU16, ByteFieldU8
from tmtccmd.cfdp import (
    IndicationCfg,
    LocalEntityCfg,
    RemoteEntityCfgTable,
    RemoteEntityCfg,
)
from tmtccmd.cfdp.defs import CfdpState, TransactionId
from tmtccmd.cfdp.handler.dest import (
    DestHandler,
    FsmResult,
    TransactionStep,
)
from tmtccmd.cfdp.user import FileSegmentRecvdParams, TransactionFinishedParams

from .cfdp_fault_handler_mock import FaultHandler
from .cfdp_user_mock import CfdpUser
from .common import CheckTimerProviderForTest


@dataclasses.dataclass
class FileInfo:
    rand_data: bytes
    file_size: int
    crc32: bytes


_FILE_COUNT = 0
_COUNTER_LOCK = Lock()


class TestDestHandlerBase(TestCase):
    def _generate_unique_filenames(self) -> Tuple[Path, Path]:
        global _FILE_COUNT
        global _COUNTER_LOCK
        with _COUNTER_LOCK:
            src_path = Path(f"{tempfile.gettempdir()}/__cfdp_test{_FILE_COUNT}.txt")
            dest_path = Path(
                f"{tempfile.gettempdir()}/__cfdp_test{_FILE_COUNT}_dest.txt"
            )
            _FILE_COUNT += 1
        return src_path, dest_path

    def common_setup(self, trans_mode: TransmissionMode):
        self.indication_cfg = IndicationCfg(True, True, True, True, True, True)
        self.fault_handler = FaultHandler()
        self.fault_handler.notice_of_cancellation_cb = MagicMock()
        self.entity_id = ByteFieldU16(2)
        self.local_cfg = LocalEntityCfg(
            self.entity_id, self.indication_cfg, self.fault_handler
        )
        self.src_entity_id = ByteFieldU16(1)
        self.src_pdu_conf = PduConfig(
            source_entity_id=self.src_entity_id,
            dest_entity_id=self.entity_id,
            transaction_seq_num=ByteFieldU8(1),
            trans_mode=trans_mode,
        )
        self.transaction_id = TransactionId(self.src_entity_id, ByteFieldU8(1))
        self.expected_mode = trans_mode
        self.closure_requested = False
        self.cfdp_user = CfdpUser()
        self.file_segment_len = 128
        self.cfdp_user.eof_recv_indication = MagicMock()
        self.cfdp_user.file_segment_recv_indication = MagicMock()
        self.cfdp_user.transaction_finished_indication = MagicMock()
        self.remote_cfg_table = RemoteEntityCfgTable()
        self.remote_cfg = RemoteEntityCfg(
            entity_id=self.src_entity_id,
            check_limit=2,
            crc_type=ChecksumType.CRC_32,
            closure_requested=False,
            crc_on_transmission=False,
            default_transmission_mode=TransmissionMode.UNACKNOWLEDGED,
            max_file_segment_len=self.file_segment_len,
            max_packet_len=self.file_segment_len,
        )
        self.remote_cfg_table.add_config(self.remote_cfg)
        self.timeout_check_limit_handling_ms = 40
        self.dest_handler = DestHandler(
            self.local_cfg,
            self.cfdp_user,
            self.remote_cfg_table,
            CheckTimerProviderForTest(
                timeout_dest_entity_ms=self.timeout_check_limit_handling_ms
            ),
        )
        self.src_file_path, self.dest_file_path = self._generate_unique_filenames()

    def _state_checker(
        self,
        fsm_res: Optional[FsmResult],
        num_packets_ready: int,
        expected_state: CfdpState,
        expected_transaction: TransactionStep,
    ):
        if fsm_res is not None:
            self.assertEqual(fsm_res.states.state, expected_state)
            self.assertEqual(fsm_res.states.step, expected_transaction)
            self.assertEqual(fsm_res.states.num_packets_ready, num_packets_ready)
            if num_packets_ready > 0:
                self.assertTrue(fsm_res.states.packets_ready)
        if expected_state != CfdpState.IDLE:
            self.assertEqual(self.dest_handler.transmission_mode, self.expected_mode)
        self.assertEqual(self.dest_handler.states.state, expected_state)
        self.assertEqual(self.dest_handler.states.step, expected_transaction)
        self.assertEqual(self.dest_handler.state, expected_state)
        self.assertEqual(self.dest_handler.step, expected_transaction)
        self.assertEqual(self.dest_handler.num_packets_ready, num_packets_ready)

    def _generic_regular_transfer_init(
        self,
        file_size: int,
    ):
        fsm_res = self._generic_transfer_init(
            file_size, 0, CfdpState.IDLE, TransactionStep.IDLE
        )
        self._state_checker(
            fsm_res, 0, CfdpState.BUSY, TransactionStep.RECEIVING_FILE_DATA
        )

    def _generic_transfer_init(
        self,
        file_size: int,
        expected_init_packets: int,
        expected_init_state: CfdpState,
        expected_init_step: TransactionStep,
    ) -> FsmResult:
        checksum_type = ChecksumType.NULL_CHECKSUM
        if file_size > 0:
            checksum_type = ChecksumType.CRC_32
        metadata_params = MetadataParams(
            checksum_type=checksum_type,
            closure_requested=self.closure_requested,
            source_file_name=self.src_file_path.as_posix(),
            dest_file_name=self.dest_file_path.as_posix(),
            file_size=file_size,
        )
        file_transfer_init = MetadataPdu(
            params=metadata_params, pdu_conf=self.src_pdu_conf
        )
        self._state_checker(
            None, expected_init_packets, expected_init_state, expected_init_step
        )
        self.dest_handler.insert_packet(file_transfer_init)
        return self.dest_handler.state_machine()

    def _insert_file_segment(
        self,
        segment: bytes,
        offset: int,
        expected_packets: int = 0,
        expected_step: TransactionStep = TransactionStep.RECEIVING_FILE_DATA,
        check_indication: bool = True,
    ) -> FsmResult:
        fd_params = FileDataParams(file_data=segment, offset=offset)
        file_data_pdu = FileDataPdu(params=fd_params, pdu_conf=self.src_pdu_conf)
        self.dest_handler.insert_packet(file_data_pdu)
        fsm_res = self.dest_handler.state_machine()
        if (
            self.indication_cfg.file_segment_recvd_indication_required
            and check_indication
        ):
            self.cfdp_user.file_segment_recv_indication.assert_called_once()
            self.assertEqual(self.cfdp_user.file_segment_recv_indication.call_count, 1)
            seg_recv_params = cast(
                FileSegmentRecvdParams,
                self.cfdp_user.file_segment_recv_indication.call_args.args[0],
            )
            self.assertEqual(seg_recv_params.transaction_id, self.transaction_id)
            self.cfdp_user.file_segment_recv_indication.reset_mock()
        self._state_checker(
            fsm_res,
            expected_packets,
            CfdpState.BUSY,
            expected_step,
        )
        return fsm_res

    def _generic_insert_eof_pdu(self, file_size: int, checksum: bytes) -> FsmResult:
        eof_pdu = EofPdu(
            file_size=file_size, file_checksum=checksum, pdu_conf=self.src_pdu_conf
        )
        self.dest_handler.insert_packet(eof_pdu)
        fsm_res = self.dest_handler.state_machine()
        if self.expected_mode == TransmissionMode.UNACKNOWLEDGED:
            if self.closure_requested:
                self._state_checker(
                    fsm_res,
                    1,
                    CfdpState.BUSY,
                    TransactionStep.SENDING_FINISHED_PDU,
                )
            else:
                self._state_checker(fsm_res, 0, CfdpState.IDLE, TransactionStep.IDLE)
        return fsm_res

    def _generic_eof_recv_indication_check(self, fsm_res: FsmResult):
        self.cfdp_user.eof_recv_indication.assert_called_once()
        self.assertEqual(
            self.cfdp_user.eof_recv_indication.call_args.args[0], self.transaction_id
        )
        self.assertEqual(fsm_res.states.transaction_id, self.transaction_id)

    def _generic_no_error_finished_pdu_check(self, fsm_res: FsmResult) -> FinishedPdu:
        self._state_checker(
            fsm_res, 1, CfdpState.BUSY, TransactionStep.SENDING_FINISHED_PDU
        )
        self.assertTrue(fsm_res.states.packets_ready)
        next_pdu = self.dest_handler.get_next_packet()
        assert next_pdu is not None
        self.assertEqual(next_pdu.pdu_type, PduType.FILE_DIRECTIVE)
        self.assertEqual(next_pdu.pdu_directive_type, DirectiveType.FINISHED_PDU)

        finished_pdu = next_pdu.to_finished_pdu()
        self.assertEqual(finished_pdu.condition_code, ConditionCode.NO_ERROR)
        self.assertEqual(finished_pdu.delivery_status, FileDeliveryStatus.FILE_RETAINED)
        self.assertEqual(finished_pdu.delivery_code, DeliveryCode.DATA_COMPLETE)
        self.assertEqual(finished_pdu.direction, Direction.TOWARDS_SENDER)
        self.assertIsNone(finished_pdu.fault_location)
        self.assertEqual(len(finished_pdu.file_store_responses), 0)
        return finished_pdu

    def _generic_verify_transfer_completion(
        self,
        fsm_res: FsmResult,
        expected_file_data: bytes,
    ):
        self._generic_transfer_finished_indication_success_check(fsm_res)
        self.assertTrue(self.dest_file_path.exists())
        self.assertEqual(self.dest_file_path.stat().st_size, len(expected_file_data))
        with open(self.dest_file_path, "rb") as file:
            self.assertEqual(expected_file_data, file.read())
        fsm_res = self.dest_handler.state_machine()
        if self.expected_mode == TransmissionMode.UNACKNOWLEDGED:
            self._state_checker(fsm_res, 0, CfdpState.IDLE, TransactionStep.IDLE)
        else:
            self._state_checker(
                fsm_res, 0, CfdpState.BUSY, TransactionStep.WAITING_FOR_FINISHED_ACK
            )

    def _generic_transfer_finished_indication_success_check(self, fsm_res: FsmResult):
        self.cfdp_user.transaction_finished_indication.assert_called_once()
        finished_params = cast(
            TransactionFinishedParams,
            self.cfdp_user.transaction_finished_indication.call_args.args[0],
        )
        self.assertEqual(finished_params.transaction_id, self.transaction_id)
        self.assertEqual(fsm_res.states.transaction_id, self.transaction_id)
        self.assertEqual(
            finished_params.finished_params.condition_code, ConditionCode.NO_ERROR
        )

    def tearDown(self) -> None:
        if self.dest_file_path.exists():
            os.remove(self.dest_file_path)
        if self.src_file_path.exists():
            os.remove(self.src_file_path)
