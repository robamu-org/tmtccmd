from spacepackets.cfdp import FaultHandlerCodes
from tmtccmd.cfdp.mib import DefaultFaultHandlerBase


class FaultHandler(DefaultFaultHandlerBase):
    def __init__(self):
        self.was_called = False
        self.call_count = 0

    def handle_fault(self, code: FaultHandlerCodes):
        self.was_called = True
        self.call_count += 1
