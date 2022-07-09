import abc
from abc import ABC
from dataclasses import dataclass
from spacepackets.cfdp.defs import (
    FaultHandlerCodes,
    ChecksumTypes,
    UnsignedByteField,
    TransmissionModes,
)


class DefaultFaultHandlerBase(ABC):
    @abc.abstractmethod
    def handle_fault(self, code: FaultHandlerCodes):
        pass


@dataclass
class LocalIndicationCfg:
    eof_sent_indication_required: bool
    eof_recv_indication_required: bool
    file_segment_recvd_indication_required: bool
    transaction_finished_indication_required: bool
    suspended_indication_required: bool
    resumed_indication_required: bool


@dataclass
class LocalEntityCfg:
    local_entity_id: UnsignedByteField
    indication_cfg: LocalIndicationCfg
    default_fault_handlers: DefaultFaultHandlerBase


@dataclass
class RemoteEntityCfg:
    remote_entity_id: UnsignedByteField
    max_file_segment_len: int
    closure_requested: bool
    crc_on_transmission: bool
    default_transmission_mode: TransmissionModes
    # TODO: Hardcoded for now
    crc_type: ChecksumTypes = ChecksumTypes.CRC_32


class RemoteEntityTable:
    def __init__(self):
        self._remote_entity_dict = dict()

    def add_remote_entity(self, cfg: RemoteEntityCfg) -> bool:
        if cfg.remote_entity_id in self._remote_entity_dict:
            return False
        self._remote_entity_dict.update({cfg.remote_entity_id: cfg})
        return True

    def get_remote_entity(self, remote_entity_id: UnsignedByteField) -> RemoteEntityCfg:
        return self._remote_entity_dict.get(remote_entity_id)
