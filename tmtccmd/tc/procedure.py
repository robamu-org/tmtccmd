import enum
from typing import Any, cast, Type, Optional

from tmtccmd.cfdp import CfdpRequestWrapper


class TcProcedureType(enum.Enum):
    DEFAULT = 0
    CFDP = 1
    CUSTOM = 2


class TcProcedureBase:
    def __init__(self, ptype: TcProcedureType):
        self.ptype = ptype


class CustomProcedureInfo(TcProcedureBase):
    def __init__(self, info: any):
        super().__init__(TcProcedureType.CUSTOM)
        self.info = info

    def __repr__(self):
        return f"{self.__class__.__name__}(info={self.info!r}"


class DefaultProcedureInfo(TcProcedureBase):
    """Generic abstraction for procedures. A procedure can be a single command or a sequence
    of commands. Generally, one procedure is mapped to a specific TC queue which is packed
    during run-time"""

    def __init__(self, service: str, op_code: str):
        super().__init__(TcProcedureType.DEFAULT)
        self.service = service
        self.op_code = op_code

    @classmethod
    def empty(cls):
        return cls("", "")

    def __repr__(self):
        return f"CmdInfo(service={self.service!r}, op_code={self.op_code!r})"


class CfdpProcedureInfo(TcProcedureBase):
    def __init__(self):
        super().__init__(TcProcedureType.CFDP)
        self.request_wrapper = CfdpRequestWrapper(None)

    @property
    def cfdp_request_type(self):
        return self.request_wrapper.request


class ProcedureWrapper:
    """Procedure helper class. It wraps the concrete procedure object but allows easily casting
    it to concrete types supported by the framework."""

    def __init__(self, base: Optional[TcProcedureBase]):
        self.base = base

    def __repr__(self):
        return f"{self.__class__.__name__}(base={self.base!r})"

    @property
    def proc_type(self):
        return self.base.ptype

    def __cast_internally(
        self,
        obj_type: Type[TcProcedureBase],
        obj: TcProcedureBase,
        expected_type: TcProcedureType,
    ) -> Any:
        if obj.ptype != expected_type:
            raise TypeError(f"Invalid object {obj} for type {self.base.ptype}")
        return cast(obj_type, obj)

    def to_def_procedure(self) -> DefaultProcedureInfo:
        return self.__cast_internally(
            DefaultProcedureInfo, self.base, TcProcedureType.DEFAULT
        )

    def to_cfdp_procedure(self) -> CfdpProcedureInfo:
        return self.__cast_internally(
            CfdpProcedureInfo, self.base, TcProcedureType.CFDP
        )

    def to_custom_procedure(self) -> CustomProcedureInfo:
        return self.__cast_internally(
            CustomProcedureInfo, self.base, TcProcedureType.CUSTOM
        )
