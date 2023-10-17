from abc import abstractmethod
from typing import Any, Optional

from .backend_state import BackendState


class BackendBase:
    @abstractmethod
    def open_com_if(self):
        """Start the backend. Raise RuntimeError on failure"""
        pass

    @abstractmethod
    def close_com_if(self):
        pass

    @abstractmethod
    def periodic_op(self, args: Optional[Any]) -> BackendState:
        pass
