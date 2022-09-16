import abc
import enum
from abc import ABC
from dataclasses import dataclass
from typing import Optional, Dict, Sequence

from spacepackets.cfdp.defs import (
    FaultHandlerCode,
    ChecksumType,
    TransmissionMode,
    CFDP_VERSION_2,
    ConditionCode,
)
from spacepackets.util import UnsignedByteField
from tmtccmd.util.countdown import Countdown


class DefaultFaultHandlerBase(ABC):
    """This base class provides a way to implement the fault handling procedures as specified
    in chapter 4.8 of the CFDP standard.

    It is passed into the CFDP handlers as part of the local entity configuration and provides
    a way to specify custom user error handlers.

    It does so by mapping each applicable CFDP :py:class:`ConditionCode` to a fault handler which
    is denoted by the four :py:class:`FaultHandlerCodes`. This code is used to dispatch
    to a user-provided callback function:

     1. `FaultHandlerCodes.IGNORE_ERROR` -> :py:meth:`ignore_cb`
     2. `FaultHandlerCodes.NOTICE_OF_CANCELLATION` -> :py:meth:`notice_of_cancellation_cb`
     3. `FaultHandlerCodes.NOTICE_OF_SUSPENSION` -> :py:meth:`notice_of_suspension_cb`
     4. `FaultHandlerCodes.ABANDON_TRANSACTION` -> :py:meth:`abandon_transaction_cb`

    For each error reported by :py:meth:`report_error`, the appropriate fault handler callback
    will be called. The user provides the callbacks by providing a custom class which implements
    these base class and all abstract fault handler callbacks.
    """

    def __init__(self):
        # The initial default handle will be to ignore the error
        self._handler_dict: Dict[ConditionCode, FaultHandlerCode] = {
            ConditionCode.POSITIVE_ACK_LIMIT_REACHED: FaultHandlerCode.IGNORE_ERROR,
            ConditionCode.KEEP_ALIVE_LIMIT_REACHED: FaultHandlerCode.IGNORE_ERROR,
            ConditionCode.INVALID_TRANSMISSION_MODE: FaultHandlerCode.IGNORE_ERROR,
            ConditionCode.FILE_CHECKSUM_FAILURE: FaultHandlerCode.IGNORE_ERROR,
            ConditionCode.FILE_SIZE_ERROR: FaultHandlerCode.IGNORE_ERROR,
            ConditionCode.FILESTORE_REJECTION: FaultHandlerCode.IGNORE_ERROR,
            ConditionCode.NAK_LIMIT_REACHED: FaultHandlerCode.IGNORE_ERROR,
            ConditionCode.INACTIVITY_DETECTED: FaultHandlerCode.IGNORE_ERROR,
            ConditionCode.CHECK_LIMIT_REACHED: FaultHandlerCode.IGNORE_ERROR,
            ConditionCode.UNSUPPORTED_CHECKSUM_TYPE: FaultHandlerCode.IGNORE_ERROR,
        }

    def get_fault_handler(self, condition: ConditionCode) -> Optional[FaultHandlerCode]:
        return self._handler_dict.get(condition)

    def set_handler(self, condition: ConditionCode, handler: FaultHandlerCode):
        if condition not in self._handler_dict:
            return
        self._handler_dict.update({condition: handler})

    def report_fault(self, condition: ConditionCode):
        if condition not in self._handler_dict:
            return
        fh_code = self._handler_dict.get(condition)
        if fh_code == FaultHandlerCode.NOTICE_OF_CANCELLATION:
            self.notice_of_cancellation_cb(condition)
        elif fh_code == FaultHandlerCode.NOTICE_OF_SUSPENSION:
            self.notice_of_suspension_cb(condition)
        elif fh_code == FaultHandlerCode.IGNORE_ERROR:
            self.ignore_cb(condition)
        elif fh_code == FaultHandlerCode.ABANDON_TRANSACTION:
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
class IndicationCfg:
    eof_sent_indication_required: bool = True
    eof_recv_indication_required: bool = True
    file_segment_recvd_indication_required: bool = True
    transaction_finished_indication_required: bool = True
    suspended_indication_required: bool = True
    resumed_indication_required: bool = True


@dataclass
class LocalEntityCfg:
    local_entity_id: UnsignedByteField
    indication_cfg: IndicationCfg
    default_fault_handlers: DefaultFaultHandlerBase


@dataclass
class RemoteEntityCfg:
    entity_id: UnsignedByteField
    max_file_segment_len: int
    closure_requested: bool
    crc_on_transmission: bool
    default_transmission_mode: TransmissionMode
    crc_type: ChecksumType
    check_limit: Optional[CheckLimitProvider]
    # NOTE: Only this version is supported
    cfdp_version: int = CFDP_VERSION_2


class RemoteEntityCfgTable:
    def __init__(self):
        self._remote_entity_dict = dict()

    def add_config(self, cfg: RemoteEntityCfg) -> bool:
        if cfg.entity_id in self._remote_entity_dict:
            return False
        self._remote_entity_dict.update({cfg.entity_id: cfg})
        return True

    def add_configs(self, cfgs: Sequence[RemoteEntityCfg]):
        for cfg in cfgs:
            if cfg.entity_id in self._remote_entity_dict:
                continue
            self._remote_entity_dict.update({cfg.entity_id: cfg})

    def get_cfg(self, remote_entity_id: UnsignedByteField) -> RemoteEntityCfg:
        return self._remote_entity_dict.get(remote_entity_id)
