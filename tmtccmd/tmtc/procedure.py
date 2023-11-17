from __future__ import annotations
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
    def __init__(self, procedure: Any):
        super().__init__(TcProcedureType.CUSTOM)
        self.procedure = procedure

    def __repr__(self):
        return f"{self.__class__.__name__}(info={self.procedure!r}"


class DefaultProcedureInfo(TcProcedureBase):
    """Generic abstraction for procedures. A procedure can be a single command or a sequence
    of commands. Generally, one procedure is mapped to a specific TC queue which is packed
    during run-time"""

    def __init__(self, cmd_path: Optional[str]):
        super().__init__(TcProcedureType.DEFAULT)
        self.cmd_path = cmd_path

    @classmethod
    def empty(cls):
        return cls(None)

    def __repr__(self):
        return f"CmdInfo(cmd_path={self.cmd_path!r})"

    def __eq__(self, other: DefaultProcedureInfo) -> bool:
        return self.cmd_path == other.cmd_path


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

    def __init__(self, procedure: Optional[TcProcedureBase]):
        self.procedure = procedure

    def __repr__(self):
        return f"{self.__class__.__name__}(base={self.procedure!r})"

    @property
    def proc_type(self):
        assert self.procedure is not None
        return self.procedure.ptype

    def __cast_internally(
        self,
        obj_type: Type[TcProcedureBase],
        obj: TcProcedureBase,
        expected_type: TcProcedureType,
    ) -> Any:
        assert self.procedure is not None
        if obj.ptype != expected_type:
            raise TypeError(f"Invalid object {obj} for type {self.procedure.ptype}")
        return cast(obj_type, obj)

    def to_def_procedure(self) -> DefaultProcedureInfo:
        assert self.procedure is not None
        return self.__cast_internally(
            DefaultProcedureInfo, self.procedure, TcProcedureType.DEFAULT
        )

    def to_cfdp_procedure(self) -> CfdpProcedureInfo:
        assert self.procedure is not None
        return self.__cast_internally(
            CfdpProcedureInfo, self.procedure, TcProcedureType.CFDP
        )

    def to_custom_procedure(self) -> CustomProcedureInfo:
        assert self.procedure is not None
        return self.__cast_internally(
            CustomProcedureInfo, self.procedure, TcProcedureType.CUSTOM
        )
