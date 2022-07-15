import abc
import enum
from abc import ABC
from dataclasses import dataclass
from typing import Optional

from spacepackets.cfdp.defs import (
    FaultHandlerCodes,
    ChecksumTypes,
    TransmissionModes,
    CFDP_VERSION_2,
)
from spacepackets.util import UnsignedByteField
from tmtccmd.util.countdown import Countdown


class DefaultFaultHandlerBase(ABC):
    @abc.abstractmethod
    def handle_fault(self, code: FaultHandlerCodes):
        pass


class EntityType(enum.IntEnum):
    SENDING = 0
    RECEIVING = 1


class CheckLimitProvider(ABC):
    @abc.abstractmethod
    def provide_check_limit(
        self,
        local_entity_id: UnsignedByteField,
        remote_entity_id: UnsignedByteField,
        entity_type: EntityType,
    ) -> Countdown:
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
    crc_type: ChecksumTypes
    check_limit: Optional[CheckLimitProvider]
    # NOTE: Only this version is supported
    cfdp_version: int = CFDP_VERSION_2


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
