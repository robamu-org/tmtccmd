from typing import Any
import logging

from time import timedelta
from spacepackets.cfdp import TransactionId, ConditionCode
from spacepackets.util import UnsignedByteField, ByteFieldU16
from tmtccmd.cfdp.user import (
    CfdpUserBase,
    FileSegmentRecvdParams,
    MetadataRecvParams,
    TransactionFinishedParams,
)

from tmtccmd.util.countdown import Countdown
from tmtccmd.cfdp.mib import (
    CheckTimerProvider,
    DefaultFaultHandlerBase,
    EntityType,
)

_LOGGER = logging.getLogger()

SOURCE_ENTITY_ID = ByteFieldU16(1)
DEST_ENTITY_ID = ByteFieldU16(2)


class CfdpFaultHandler(DefaultFaultHandlerBase):
    def notice_of_suspension_cb(
        self, transaction_id: TransactionId, cond: ConditionCode, progress: int
    ):
        _LOGGER.warning(
            f"Received Notice of Suspension for transaction {transaction_id!r} with condition "
            f"code {cond!r}. Progress: {progress}"
        )

    def notice_of_cancellation_cb(
        self, transaction_id: TransactionId, cond: ConditionCode, progress: int
    ):
        _LOGGER.warning(
            f"Received Notice of Cancellation for transaction {transaction_id!r} with condition "
            f"code {cond!r}. Progress: {progress}"
        )

    def abandoned_cb(
        self, transaction_id: TransactionId, cond: ConditionCode, progress: int
    ):
        _LOGGER.warning(
            f"Received Abanadoned Fault for transaction {transaction_id!r} with condition "
            f"code {cond!r}. Progress: {progress}"
        )

    def ignore_cb(
        self, transaction_id: TransactionId, cond: ConditionCode, progress: int
    ):
        _LOGGER.warning(
            f"Ignored Fault for transaction {transaction_id!r} with condition "
            f"code {cond!r}. Progress: {progress}"
        )


class CfdpUser(CfdpUserBase):
    def __init__(self, base_str: str):
        self.base_str = base_str
        super().__init__()

    def transaction_indication(self, transaction_id: TransactionId):
        """This indication is used to report the transaction ID to the CFDP user"""
        _LOGGER.info(f"{self.base_str}: Transaction.indication for {transaction_id}")

    def eof_sent_indication(self, transaction_id: TransactionId):
        _LOGGER.info(f"{self.base_str}: EOF-Sent.indication for {transaction_id}")

    def transaction_finished_indication(self, params: TransactionFinishedParams):
        _LOGGER.info(
            f"{self.base_str}: Transaction-Finished.indication for {params.transaction_id}."
        )

    def metadata_recv_indication(self, params: MetadataRecvParams):
        _LOGGER.info(
            f"{self.base_str}: Metadata-Recv.indication for {params.transaction_id}."
        )

    def file_segment_recv_indication(self, params: FileSegmentRecvdParams):
        _LOGGER.info(
            f"{self.base_str}: File-Segment-Recv.indication for {params.transaction_id}."
        )

    def report_indication(self, transaction_id: TransactionId, status_report: Any):
        # TODO: p.28 of the CFDP standard specifies what information the status report parameter
        #       could contain. I think it would be better to not hardcode the type of the status
        #       report here, but something like Union[any, CfdpStatusReport] with CfdpStatusReport
        #       being an implementation which supports all three information suggestions would be
        #       nice
        pass

    def suspended_indication(
        self, transaction_id: TransactionId, cond_code: ConditionCode
    ):
        _LOGGER.info(
            f"{self.base_str}: Suspended.indication for {transaction_id} | Condition Code: {cond_code}"
        )

    def resumed_indication(self, transaction_id: TransactionId, progress: int):
        _LOGGER.info(
            f"{self.base_str}: Resumed.indication for {transaction_id} | Progress: {progress} bytes"
        )

    def fault_indication(
        self, transaction_id: TransactionId, cond_code: ConditionCode, progress: int
    ):
        _LOGGER.info(
            f"{self.base_str}: Fault.indication for {transaction_id} | Condition Code: {cond_code} | "
            f"Progress: {progress} bytes"
        )

    def abandoned_indication(
        self, transaction_id: TransactionId, cond_code: ConditionCode, progress: int
    ):
        _LOGGER.info(
            f"{self.base_str}: Abandoned.indication for {transaction_id} | Condition Code: {cond_code} |"
            f" Progress: {progress} bytes"
        )

    def eof_recv_indication(self, transaction_id: TransactionId):
        _LOGGER.info(f"{self.base_str}: EOF-Recv.indication for {transaction_id}")


class CustomCheckTimerProvider(CheckTimerProvider):
    def provide_check_timer(
        self,
        local_entity_id: UnsignedByteField,
        remote_entity_id: UnsignedByteField,
        entity_type: EntityType,
    ) -> Countdown:
        return Countdown(timedelta(seconds=5.0))
