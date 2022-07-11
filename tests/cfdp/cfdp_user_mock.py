from typing import Optional, List

from spacepackets.cfdp import ConditionCode, FileStoreResponseTlv
from spacepackets.cfdp.pdu import FileDeliveryStatus, DeliveryCode
from tmtccmd.cfdp import CfdpUserBase, TransactionId


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

    def transaction_finished_indication(
        self,
        transaction_id: TransactionId,
        condition_code: ConditionCode,
        file_status: FileDeliveryStatus,
        delivery_code: DeliveryCode,
        _fs_responses: Optional[List[FileStoreResponseTlv]] = None,
        _status_report: Optional[any] = None,
    ):
        self.transaction_finished_was_called = True
        self.transaction_finished_call_count += 1

    def eof_sent_indication(self, transaction_id: TransactionId):
        self.eof_sent_indication_was_called = True
        self.eof_sent_indication_call_count += 1

    def abandon_indication(
        self, transaction_id: int, cond_code: ConditionCode, progress: int
    ):
        pass
