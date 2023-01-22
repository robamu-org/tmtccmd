from spacepackets.cfdp import ConditionCode
from tmtccmd.cfdp.mib import DefaultFaultHandlerBase


class FaultHandler(DefaultFaultHandlerBase):
    def __init__(self):
        super().__init__()
        self.notice_of_suspension_called = False
        self.notice_of_suspension_call_count = 0

    def notice_of_suspension_cb(self, cond: ConditionCode):
        self.notice_of_suspension_called = True
        self.notice_of_suspension_call_count += 1

    def notice_of_cancellation_cb(self, cond: ConditionCode):
        pass

    def abandoned_cb(self, cond: ConditionCode):
        pass

    def ignore_cb(self, cond: ConditionCode):
        pass
