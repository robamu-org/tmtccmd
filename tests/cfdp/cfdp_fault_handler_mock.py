from spacepackets.cfdp import ConditionCode
from tmtccmd.cfdp.mib import DefaultFaultHandlerBase


class FaultHandler(DefaultFaultHandlerBase):
    def __init__(self):
        super().__init__()

    def notice_of_suspension_cb(self, _: ConditionCode):
        pass

    def notice_of_cancellation_cb(self, _: ConditionCode):
        pass

    def abandoned_cb(self, _: ConditionCode):
        pass

    def ignore_cb(self, _: ConditionCode):
        pass
