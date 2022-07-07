import dataclasses
import enum


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
    INITIALIZE = 1
    CRC_PROCEDURE = 2
    # The following three are used for the Copy File Procedure
    SENDING_METADATA = 3
    SENDING_FILE_DATA = 4
    SENDING_EOF = 5
    SENDING_ACK = 6
    DONE = 7


class SourceState(enum.Enum):
    IDLE = 0
    BUSY_CLASS_1_NACKED = 1
    BUSY_CLASS_2_ACKED = 2
    SUSPENDED = 3


class CfdpDestState(enum.Enum):
    pass


# TODO: It might become necessary to introduce substates for handling CFDP requests
class CfdpStates(enum.Enum):
    IDLE = 0
    TX_PENDING = 1
    RX_PENDING = 2


@dataclasses.dataclass
class SourceStateWrapper:
    state = SourceState.IDLE
    transaction = SourceTransactionState.IDLE


@dataclasses.dataclass
class StateWrapper:
    state: CfdpStates
    source_handler_state: SourceStateWrapper()


class TransactionId:
    def __init__(self, source_entity_id: bytes, transaction_seq_num: bytes):
        pass


class ByteFlowControl:
    period: float
    max_bytes: int


class BusyError(Exception):
    pass


class SequenceNumberOverflow(Exception):
    pass
