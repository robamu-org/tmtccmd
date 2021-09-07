from typing import Tuple, List
import enum

from tmtccmd.pus import ObjectId
from tmtccmd.ecss.tm import PusTelemetry


class HkContentType(enum.Enum):
    HK = enum.auto()
    DEFINITIONS = enum.auto()


class Service3Base:
    """Base class. The TMTC core provides a Service 3 implementation which is intended to be used
    with the FSFW. However, users can define an own Service 3 implementation.

    The TMTC printer utility uses the fields defined in this base class to perform prinouts so
    if a custom class is defined, the user should implement this class and fill the fields
    in the TM handling hook if printout of the HK field and validity checking is desired.
    """
    def __init__(self, object_id: int, custom_hk_handling: bool = False):
        self._object_id = ObjectId(object_id=object_id)
        self._set_id = 0
        self._param_length = 0
        self._custom_hk_handling = custom_hk_handling

    def get_object_id(self) -> ObjectId:
        return self._object_id

    def get_set_id(self) -> int:
        return self._set_id

    def has_custom_hk_handling(self) -> bool:
        return self._custom_hk_handling

    def set_custom_hk_handling(self, custom_hk_handling: bool):
        self._custom_hk_handling = custom_hk_handling

    def get_hk_definitions_list(self) -> Tuple[List, List]:
        """Can be implemented by a child class to print definitions lists. The first list
        should contain a header with parameter names, and the second list shall contain the
        corresponding set IDs"""
        return [], []
