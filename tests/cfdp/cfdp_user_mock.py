from spacepackets.cfdp import ConditionCode
from tmtccmd.cfdp import CfdpUserBase, TransactionId
from tmtccmd.cfdp.user import (
    FileSegmentRecvParams,
    MetadataRecvParams,
    TransactionFinishedParams,
)


class CfdpUser(CfdpUserBase):
    def __init__(self):
        super().__init__()
        self.transaction_inidcation_was_called = False
        self.transaction_inidcation_call_count = 0
        self.transaction_finished_was_called = False
        self.transaction_finished_call_count = 0
        self.eof_sent_indication_was_called = False
        self.eof_sent_indication_call_count = 0

    def transaction_indication(self, transaction_id: TransactionId):
        self.transaction_inidcation_was_called = True
        self.transaction_inidcation_call_count += 1

    def transaction_finished_indication(self, params: TransactionFinishedParams):
        self.transaction_finished_was_called = True
        self.transaction_finished_call_count += 1

    def eof_sent_indication(self, transaction_id: TransactionId):
        self.eof_sent_indication_was_called = True
        self.eof_sent_indication_call_count += 1

    def abandon_indication(
        self, transaction_id: int, cond_code: ConditionCode, progress: int
    ):
        pass

    def metadata_recv_indication(self, params: MetadataRecvParams):
        pass

    def file_segment_recv_indication(self, params: FileSegmentRecvParams):
        pass

    def report_indication(self, transaction_id: TransactionId, status_report: any):
        pass

    def suspended_indication(
        self, transaction_id: TransactionId, cond_code: ConditionCode
    ):
        pass

    def resumed_indication(self, transaction_id: TransactionId, progress: int):
        pass

    def fault_indication(
        self, transaction_id: TransactionId, cond_code: ConditionCode, progress: int
    ):
        pass

    def abandoned_indication(
        self, transaction_id: TransactionId, cond_code: ConditionCode, progress: int
    ):
        pass

    def eof_recv_indication(self, transaction_id: TransactionId):
        pass
