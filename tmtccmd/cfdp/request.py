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
from spacepackets.cfdp.defs import UnsignedByteField
from tmtccmd.cfdp.defs import CfdpRequestType
import dataclasses


class CfdpRequestBase:
    def __init__(self, req_type: CfdpRequestType):
        self.req_type = req_type


@dataclasses.dataclass
class PutRequestCfg:
    destination_id: UnsignedByteField
    # All the following fields are optional because a put request can also be a metadata-only
    # request
    source_file: Optional[Path]
    dest_file: Optional[str]
    trans_mode: Optional[TransmissionModes]
    closure_requested: Optional[bool]
    seg_ctrl: SegmentationControl = Optional[
        SegmentationControl.NO_RECORD_BOUNDARIES_PRESERVATION
    ]
    fault_handler_overrides: Optional[FaultHandlerOverrideTlv] = None
    flow_label_tlv: Optional[FlowLabelTlv] = None
    msgs_to_user: Optional[List[MessageToUserTlv]] = None
    fs_requests: Optional[List[FileStoreRequestTlv]] = None


class PutRequest(CfdpRequestBase):
    def __init__(self, cfg: PutRequestCfg):
        super().__init__(CfdpRequestType.PUT)
        self.cfg = cfg


class CfdpRequestWrapper:
    def __init__(self, base: Optional[CfdpRequestBase]):
        self.base = base

    @property
    def request_type(self) -> CfdpRequestType:
        return self.base.req_type

    @property
    def request(self) -> CfdpRequestType:
        return self.base.req_type

    def to_put_request(self) -> PutRequest:
        if self.base.req_type != CfdpRequestType.PUT:
            raise TypeError(f"Request is not a {PutRequest.__name__}: {self.base!r}")
        return cast(PutRequest, self.base)
