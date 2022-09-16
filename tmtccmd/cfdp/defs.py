from __future__ import annotations

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


class CfdpStates(enum.Enum):
    IDLE = 0
    BUSY_CLASS_1_NACKED = 1
    BUSY_CLASS_2_ACKED = 2
    SUSPENDED = 3


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

    def __str__(self):
        return (
            f"Transaction {{ Source ID {{{self.source_id}}}, Sequence "
            f"number {self.seq_num.value} }}"
        )

    def __eq__(self, other: TransactionId):
        return self.source_id == other.source_id and self.seq_num == other.seq_num

    def __hash__(self):
        return hash((self.source_id, self.seq_num))


class SequenceNumberOverflow(Exception):
    pass
