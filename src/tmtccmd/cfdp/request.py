from typing import Optional, cast

from cfdppy.defs import CfdpRequestType
from tmtccmd.config.defs import CfdpParams


class CfdpRequestBase:
    def __init__(self, req_type: CfdpRequestType):
        self.req_type = req_type


class PutRequestCfgWrapper(CfdpRequestBase):
    def __init__(self, cfg: CfdpParams):
        super().__init__(CfdpRequestType.PUT)
        self.cfg = cfg

    def __repr__(self):
        return f"{self.__class__.__name__}(cfg={self.cfg})"


class CfdpRequestWrapper:
    def __init__(self, base: Optional[CfdpRequestBase]):
        self.base = base

    @property
    def request_type(self) -> CfdpRequestType:
        return self.base.req_type

    @property
    def request(self) -> CfdpRequestType:
        return self.base.req_type

    def to_put_request(self) -> PutRequestCfgWrapper:
        if self.base.req_type != CfdpRequestType.PUT:
            raise TypeError(f"Request is not a {PutRequestCfgWrapper.__name__}: {self.base!r}")
        return cast(PutRequestCfgWrapper, self.base)
