from dataclasses import dataclass

from tmtccmd.cfdp.defs import CfdpStates, DestTransactionState


@dataclass
class DestStateWrapper:
    state: CfdpStates = CfdpStates.IDLE
    transaction: DestTransactionState = DestTransactionState.IDLE
    packet_ready: bool = True


class DestHandler:
    pass
