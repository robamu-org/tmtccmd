from __future__ import annotations
import enum
from typing import Any, cast, Type, Optional

from tmtccmd.cfdp import CfdpRequestWrapper


class TcProcedureType(enum.Enum):
    TREE_COMMANDING = 0
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


class TreeCommandingProcedure(TcProcedureBase):
    """Generic abstraction for procedures. A procedure can be a single command or a sequence
    of commands. Generally, one procedure is mapped to a specific TC queue which is packed
    during run-time"""

    def __init__(self, cmd_path: Optional[str]):
        super().__init__(TcProcedureType.TREE_COMMANDING)
        self.cmd_path = cmd_path

    @classmethod
    def empty(cls):
        return cls(None)

    def __repr__(self):
        return f"CmdInfo(cmd_path={self.cmd_path!r})"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, TreeCommandingProcedure):
            return self.cmd_path == other.cmd_path
        return False


class CfdpProcedure(TcProcedureBase):
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

    def to_tree_commanding_procedure(self) -> TreeCommandingProcedure:
        assert self.procedure is not None
        return self.__cast_internally(
            TreeCommandingProcedure, self.procedure, TcProcedureType.TREE_COMMANDING
        )

    def to_cfdp_procedure(self) -> CfdpProcedure:
        assert self.procedure is not None
        return self.__cast_internally(CfdpProcedure, self.procedure, TcProcedureType.CFDP)

    def to_custom_procedure(self) -> CustomProcedureInfo:
        assert self.procedure is not None
        return self.__cast_internally(CustomProcedureInfo, self.procedure, TcProcedureType.CUSTOM)
