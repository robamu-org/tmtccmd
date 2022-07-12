import enum
from dataclasses import dataclass

from spacepackets.cfdp.pdu.helper import GenericPduPacket, PduHolder
from tmtccmd.cfdp import RemoteEntityCfg
from tmtccmd.cfdp.defs import CfdpStates


class TransactionStep(enum.Enum):
    IDLE = 0
    # Metadata was received
    TRANSACTION_START = 1
    CRC_PROCEDURE = 2
    RECEIVING_FILE_DATA = 3
    # EOF was received. Perform checksum verification and notice of completion
    TRANSFER_COMPLETION = 4
    SEINDING_FINISHED_PDU = 5


@dataclass
class DestStateWrapper:
    state: CfdpStates = CfdpStates.IDLE
    transaction: TransactionStep = TransactionStep.IDLE
    packet_ready: bool = True


class FsmResult:
    def __init__(self, states: DestStateWrapper, pdu_holder: PduHolder):
        self.states = states
        self.pdu_holder = pdu_holder


class DestHandler:
    def __init__(self, cfg: RemoteEntityCfg):
        self.cfg = cfg
        self.states = DestStateWrapper()
        self._pdu_holder = PduHolder(None)

    def _start_transaction(self) -> bool:
        if self.states.state != CfdpStates.IDLE:
            return False
        return True

    def state_machine(self) -> FsmResult:
        if self.states.state == CfdpStates.IDLE:
            return FsmResult(self.states, self._pdu_holder)
        elif self.states.state == CfdpStates.BUSY_CLASS_1_NACKED:
            pass
        return FsmResult(self.states, self._pdu_holder)

    def pass_packet(self, packet: GenericPduPacket):
        pass
