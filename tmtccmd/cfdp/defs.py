from __future__ import annotations

import dataclasses
import enum

from spacepackets.util import UnsignedByteField


class CfdpRequestType(enum.Enum):
    PUT = 0
    REPORT = 1
    CANCEL = 2
    SUSPEND = 3
    RESUME = 4


class CfdpIndication(enum.Enum):
    TRANSACTION = 0
    EOF = 1
    FINISHED = 2
    METADATA = 3
    FILE_SEGMENT_RECV = 4
    REPORT = 5
    SUSPENDED = 6
    RESUMED = 7
    FAULT = 8
    ABANDONED = 9
    EOF_RECV = 10


class SourceTransactionState(enum.Enum):
    IDLE = 0
    TRANSACTION_START = 1
    CRC_PROCEDURE = 2
    # The following three are used for the Copy File Procedure
    SENDING_METADATA = 3
    SENDING_FILE_DATA = 4
    SENDING_EOF = 5
    SENDING_ACK = 6
    NOTICE_OF_COMPLETION = 7


class DestTransactionState(enum.Enum):
    IDLE = 0
    # Metadata was received
    TRANSACTION_START = 1
    CRC_PROCEDURE = 2
    RECEIVING_FILE_DATA = 3
    # EOF was received. Perform checksum verification and notice of completion
    TRANSFER_COMPLETION = 4
    SEINDING_FINISHED_PDU = 5


class CfdpStates(enum.Enum):
    IDLE = 0
    BUSY_CLASS_1_NACKED = 1
    BUSY_CLASS_2_ACKED = 2
    SUSPENDED = 3


@dataclasses.dataclass
class SourceStateWrapper:
    state = CfdpStates.IDLE
    step = SourceTransactionState.IDLE
    packet_ready = True


@dataclasses.dataclass
class DestStateWrapper:
    state = CfdpStates.IDLE
    transaction = DestTransactionState.IDLE
    packet_ready = True


@dataclasses.dataclass
class StateWrapper:
    source_handler_state: SourceStateWrapper = SourceStateWrapper()
    dest_handler_state: DestStateWrapper = DestStateWrapper()


class TransactionId:
    def __init__(
        self,
        source_entity_id: UnsignedByteField,
        transaction_seq_num: UnsignedByteField,
    ):
        self.source_id = source_entity_id
        self.seq_num = transaction_seq_num

    def __repr__(self):
        return (
            f"{self.__class__.__name__}(source_entity_id={self.source_id!r}, "
            f"transaction_seq_num={self.seq_num!r})"
        )

    def __eq__(self, other: TransactionId):
        return self.source_id == other.source_id and self.seq_num == other.seq_num

    def __hash__(self):
        return hash((self.source_id, self.seq_num))


class ByteFlowControl:
    period: float
    max_bytes: int


class BusyError(Exception):
    pass


class SequenceNumberOverflow(Exception):
    pass
