from spacepackets.cfdp import ConditionCode
from tmtccmd.cfdp import CfdpUserBase, TransactionId
from tmtccmd.cfdp.user import (
    FileSegmentRecvdParams,
    MetadataRecvParams,
    TransactionFinishedParams,
)


class CfdpUser(CfdpUserBase):
    def __init__(self):
        super().__init__()

    def transaction_indication(self, transaction_id: TransactionId):
        pass

    def transaction_finished_indication(self, params: TransactionFinishedParams):
        pass

    def eof_sent_indication(self, transaction_id: TransactionId):
        pass

    def abandon_indication(
        self, transaction_id: int, cond_code: ConditionCode, progress: int
    ):
        pass

    def metadata_recv_indication(self, params: MetadataRecvParams):
        pass

    def file_segment_recv_indication(self, params: FileSegmentRecvdParams):
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
