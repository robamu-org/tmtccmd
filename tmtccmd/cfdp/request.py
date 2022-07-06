from pathlib import Path
from typing import Optional, List, cast

from spacepackets.cfdp import (
    SegmentationControl,
    TransmissionModes,
    FaultHandlerOverrideTlv,
    FlowLabelTlv,
    MessageToUserTlv,
    FileStoreRequestTlv,
)
from tmtccmd.cfdp.defs import CfdpRequest
import dataclasses


class CfdpRequestBase:
    def __init__(self, request: CfdpRequest):
        self.request = request


@dataclasses.dataclass
class PutRequestCfg:
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


class PutRequest(CfdpRequestBase):
    def __init__(self, cfg: PutRequestCfg):
        super().__init__(CfdpRequest.PUT)
        self.cfg = cfg


class CfdpRequestWrapper:
    def __init__(self, base: Optional[CfdpRequestBase]):
        self.base = base

    @property
    def request(self) -> CfdpRequest:
        return self.base.request

    def to_put_request(self) -> PutRequest:
        if self.base.request != CfdpRequest.PUT:
            raise TypeError(f"Request is not a {PutRequest.__name__}: {self.base!r}")
        return cast(PutRequest, self.base)
