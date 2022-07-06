import dataclasses
import enum
from pathlib import Path
from typing import Optional, List

from spacepackets.cfdp.defs import SegmentationControl, TransmissionModes
from spacepackets.cfdp.tlv import (
    FaultHandlerOverrideTlv,
    FlowLabelTlv,
    MessageToUserTlv,
    FileStoreRequestTlv,
)


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


@dataclasses.dataclass
class PutRequest:
    destination_id: bytes
    source_file: Path
    dest_file: str
    seg_ctrl: SegmentationControl
    trans_mode: TransmissionModes
    closure_requested: bool
    fault_handler_overrides: Optional[FaultHandlerOverrideTlv] = None
    flow_label_tlv: Optional[FlowLabelTlv] = None
    msgs_to_user: Optional[List[MessageToUserTlv]] = None
    fs_requests: Optional[List[FileStoreRequestTlv]] = None


class CfdpStates(enum.Enum):
    IDLE = 0
    CRC_PROCEDURE = 1
    SENDING_METADATA = 2
    SENDING_FILE_DATA_PDUS = 3
    SENDING_EOF_DATA_PDU = 4
    SENDING_FINISH_PDU = 5
    SEND_ACK_PDU = 6


class ByteFlowControl:
    period: float
    max_bytes: int


class BusyError(Exception):
    pass


class SequenceNumberOverflow(Exception):
    pass
