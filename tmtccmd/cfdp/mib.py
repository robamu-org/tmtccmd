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
    is denoted by the four :py:class:`spacepackets.cfdp.defs.FaultHandlerCode` s. This code is used
    to dispatch to a user-provided callback function:

     1. `IGNORE_ERROR` -> :py:meth:`ignore_cb`
     2. `NOTICE_OF_CANCELLATION` -> :py:meth:`notice_of_cancellation_cb`
     3. `NOTICE_OF_SUSPENSION` -> :py:meth:`notice_of_suspension_cb`
     4. `ABANDON_TRANSACTION` -> :py:meth:`abandon_transaction_cb`

    For each error reported by :py:meth:`report_fault`, the appropriate fault handler callback
    will be called. The user provides the callbacks by providing a custom class which implements
    these base class and all abstract fault handler callbacks.
    """

    def __init__(self):
        # The initial default handle will be to cancel the transaction
        self._handler_dict: Dict[ConditionCode, FaultHandlerCode] = {
            ConditionCode.CANCEL_REQUEST_RECEIVED: FaultHandlerCode.NOTICE_OF_CANCELLATION,
            ConditionCode.POSITIVE_ACK_LIMIT_REACHED: FaultHandlerCode.NOTICE_OF_CANCELLATION,
            ConditionCode.KEEP_ALIVE_LIMIT_REACHED: FaultHandlerCode.NOTICE_OF_CANCELLATION,
            ConditionCode.INVALID_TRANSMISSION_MODE: FaultHandlerCode.NOTICE_OF_CANCELLATION,
            ConditionCode.FILE_CHECKSUM_FAILURE: FaultHandlerCode.NOTICE_OF_CANCELLATION,
            ConditionCode.FILE_SIZE_ERROR: FaultHandlerCode.NOTICE_OF_CANCELLATION,
            ConditionCode.FILESTORE_REJECTION: FaultHandlerCode.NOTICE_OF_CANCELLATION,
            ConditionCode.NAK_LIMIT_REACHED: FaultHandlerCode.NOTICE_OF_CANCELLATION,
            ConditionCode.INACTIVITY_DETECTED: FaultHandlerCode.NOTICE_OF_CANCELLATION,
            ConditionCode.CHECK_LIMIT_REACHED: FaultHandlerCode.NOTICE_OF_CANCELLATION,
            ConditionCode.UNSUPPORTED_CHECKSUM_TYPE: FaultHandlerCode.NOTICE_OF_CANCELLATION,
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
    """This models the remote entity configuration information as specified in chapter 8.3
    of the CFDP standard.

    Some of the fields which were not considered necessary for the Python implementation
    were omitted. Some other fields which are not contained inside the standard but are considered
    necessary for the Python implementation are included.

    Arguments
    -----------
    entity_id:
        The ID of the remote entity.
    max_file_segment_len:
        The maximum file segment length which determines the maximum size
        of file data PDUs in addition to the `max_packet_len` attribute.
    max_packet_len:
        This determines of all PDUs generated for that remote entity in addition to the
        `max_file_segment_len` attribute which also determines the size of file data PDUs.
    closure_requested:
        If the closure requested field is not supplied as part of the Put Request, it will be
        determined from this field in the remote configuration.
    crc_on_transmission:
        If the CRC option is not supplied as part of the Put Request, it will be
        determined from this field in the remote configuration.
    default_transmission_mode:
        If the transmission mode is not supplied as part of the Put Request, it will be
        determined from this field in the remote configuration.
    crc_type:
        Default checksum type used to calculate for all file transmissions to this remote entity.
    check_limit_provider:
        Both the source and destination handler use a check limit for the unacknowledged mode.
        This generic provider allows the user to configure the check limit at run time as well.

    """

    entity_id: UnsignedByteField
    max_file_segment_len: int
    max_packet_len: int
    closure_requested: bool
    crc_on_transmission: bool
    default_transmission_mode: TransmissionMode
    crc_type: ChecksumType
    check_limit_provider: Optional[CheckLimitProvider]
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

    def get_cfg(self, remote_entity_id: UnsignedByteField) -> Optional[RemoteEntityCfg]:
        return self._remote_entity_dict.get(remote_entity_id)
