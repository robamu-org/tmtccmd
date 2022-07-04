from dataclasses import dataclass
from typing import Callable
from spacepackets.cfdp.definitions import FaultHandlerCodes

# User can specify a function which takes the fault handler code as an argument and returns nothing
FaultHandlerT = Callable[[FaultHandlerCodes], None]


@dataclass
class LocalEntityCfg:
    local_entity_id: bytes
    eof_sent_indication_required: bool
    eof_recv_indication_required: bool
    file_segment_recvd_required: bool
    transaction_finished_indication_required: bool
    suspended_indication_required: bool
    resumed_indication_required: bool
    default_fault_handlers: FaultHandlerT
    length_seq_num: int = 2
    # I'm just going to assume that 255 possible IDs are sufficient for most applications
    length_entity_ids: int = 1
