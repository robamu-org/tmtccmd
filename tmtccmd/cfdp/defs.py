import dataclasses
import enum


class CfdpRequest(enum.Enum):
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


class CfdpTransferState(enum.Enum):
    IDLE = 0
    INITIALIZE = 1
    CRC_PROCEDURE = 2
    # The following three are used for the Copy File Procedure
    SENDING_METADATA = 3
    SENDING_FILE_DATA = 4
    SENDING_EOF = 5
    SENDING_FINISH = 6


class CfdpReceptionState(enum.Enum):
    pass


# TODO: It might become necessary to introduce substates for handling CFDP requests
class CfdpStates(enum.Enum):
    IDLE = 0
    OP_PENDING = 1


@dataclasses.dataclass
class CfdpStateWrapper:
    state: CfdpStates
    transfer_state: CfdpTransferState


class ByteFlowControl:
    period: float
    max_bytes: int


class BusyError(Exception):
    pass


class SequenceNumberOverflow(Exception):
    pass
