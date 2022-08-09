import abc
import enum
from abc import ABC
from dataclasses import dataclass
from typing import Optional, Dict

from spacepackets.cfdp.defs import (
    FaultHandlerCodes,
    ChecksumTypes,
    TransmissionModes,
    CFDP_VERSION_2,
    ConditionCode,
)
from spacepackets.util import UnsignedByteField
from tmtccmd.util.countdown import Countdown


class DefaultFaultHandlerBase(ABC):
    def __init__(self):
        # The initial default handle will be to ignore the error
        self._handler_dict: Dict[ConditionCode, FaultHandlerCodes] = {
            ConditionCode.POSITIVE_ACK_LIMIT_REACHED: FaultHandlerCodes.IGNORE_ERROR,
            ConditionCode.KEEP_ALIVE_LIMIT_REACHED: FaultHandlerCodes.IGNORE_ERROR,
            ConditionCode.INVALID_TRANSMISSION_MODE: FaultHandlerCodes.IGNORE_ERROR,
            ConditionCode.FILE_CHECKSUM_FAILURE: FaultHandlerCodes.IGNORE_ERROR,
            ConditionCode.FILE_SIZE_ERROR: FaultHandlerCodes.IGNORE_ERROR,
            ConditionCode.FILESTORE_REJECTION: FaultHandlerCodes.IGNORE_ERROR,
            ConditionCode.NAK_LIMIT_REACHED: FaultHandlerCodes.IGNORE_ERROR,
            ConditionCode.INACTIVITY_DETECTED: FaultHandlerCodes.IGNORE_ERROR,
            ConditionCode.CHECK_LIMIT_REACHED: FaultHandlerCodes.IGNORE_ERROR,
            ConditionCode.UNSUPPORTED_CHECKSUM_TYPE: FaultHandlerCodes.IGNORE_ERROR,
        }

    def get_fault_handler(
        self, condition: ConditionCode
    ) -> Optional[FaultHandlerCodes]:
        return self._handler_dict.get(condition)

    def set_handler(self, condition: ConditionCode, handler: FaultHandlerCodes):
        if condition not in self._handler_dict:
            return
        self._handler_dict.update({condition: handler})

    def fault_callback(self, condition: ConditionCode):
        if condition not in self._handler_dict:
            return
        fh_code = self._handler_dict.get(condition)
        if fh_code == FaultHandlerCodes.NOTICE_OF_CANCELLATION:
            self.notice_of_cancellation_cb(condition)
        elif fh_code == FaultHandlerCodes.NOTICE_OF_SUSPENSION:
            self.notice_of_suspension_cb(condition)
        elif fh_code == FaultHandlerCodes.IGNORE_ERROR:
            self.ignore_cb(condition)
        elif fh_code == FaultHandlerCodes.ABANDON_TRANSACTION:
            self.abandoned_cb(condition)

    @abc.abstractmethod
    def notice_of_suspension_cb(self, cond: ConditionCode):
        pass

    @abc.abstractmethod
    def notice_of_cancellation_cb(self, cond: ConditionCode):
        pass

    @abc.abstractmethod
    def abandoned_cb(self, cond: ConditionCode):
        pass

    @abc.abstractmethod
    def ignore_cb(self, cond: ConditionCode):
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
    entity_id: UnsignedByteField
    max_file_segment_len: int
    closure_requested: bool
    crc_on_transmission: bool
    default_transmission_mode: TransmissionModes
    crc_type: ChecksumTypes
    check_limit: Optional[CheckLimitProvider]
    # NOTE: Only this version is supported
    cfdp_version: int = CFDP_VERSION_2


class RemoteEntityCfgTable:
    def __init__(self):
        self._remote_entity_dict = dict()

    def add_remote_entity(self, cfg: RemoteEntityCfg) -> bool:
        if cfg.entity_id in self._remote_entity_dict:
            return False
        self._remote_entity_dict.update({cfg.entity_id: cfg})
        return True

    def get_remote_entity(self, remote_entity_id: UnsignedByteField) -> RemoteEntityCfg:
        return self._remote_entity_dict.get(remote_entity_id)
