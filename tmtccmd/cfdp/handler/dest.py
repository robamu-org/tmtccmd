from dataclasses import dataclass

from tmtccmd.cfdp.defs import CfdpStates, DestTransactionState


@dataclass
class DestStateWrapper:
    state = CfdpStates.IDLE
    transaction = DestTransactionState.IDLE
    packet_ready = True


class DestHandler:
    pass
