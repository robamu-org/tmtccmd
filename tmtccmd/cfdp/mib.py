from dataclasses import dataclass
from typing import Callable
from spacepackets.cfdp.defs import FaultHandlerCodes

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


@dataclass
class RemoteEntityCfg:
    remote_entity_id: bytes
    max_file_segment_len: int
    crc_on_transmission: bool


class RemoteEntityTable:
    def __init__(self):
        self._remote_entity_dict = dict()

    def add_remote_entity(self, cfg: RemoteEntityCfg) -> bool:
        if cfg.remote_entity_id in self._remote_entity_dict:
            return False
        self._remote_entity_dict.update({cfg.remote_entity_id: cfg})
        return True

    def get_remote_entity(self, remote_entity_id: bytes) -> RemoteEntityCfg:
        return self._remote_entity_dict.get(remote_entity_id)
