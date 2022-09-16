from typing import Tuple, List
import enum

from tmtccmd.util.obj_id import ObjectIdU32


class HkContentType(enum.Enum):
    HK = enum.auto
    DEFINITIONS = enum.auto


class Service3Base:
    """Base class. The TMTC core provides a Service 3 implementation which is intended to be used
    with the FSFW. However, users can define an own Service 3 implementation.

    The TMTC printer utility uses the fields defined in this base class to perform prinouts so
    if a custom class is defined, the user should implement this class and fill the fields
    in the TM handling hook if printout of the HK field and validity checking is desired.
    """

    def __init__(self, object_id: int, custom_hk_handling: bool = False):
        self._object_id = ObjectIdU32(obj_id=object_id)
        self._set_id = 0
        self._param_length = 0
        self._custom_hk_handling = custom_hk_handling

    @property
    def object_id(self) -> ObjectIdU32:
        return self._object_id

    @object_id.setter
    def object_id(self, obj_id: ObjectIdU32):
        self._object_id = obj_id

    @property
    def set_id(self) -> int:
        return self._set_id

    @set_id.setter
    def set_id(self, set_id: int):
        self._set_id = set_id

    @property
    def has_custom_hk_handling(self) -> bool:
        return self._custom_hk_handling

    @has_custom_hk_handling.setter
    def has_custom_hk_handling(self, has_custom_hk_handling: bool):
        self._custom_hk_handling = has_custom_hk_handling

    @property
    def hk_definitions_list(self) -> Tuple[List, List]:
        """Can be implemented by a child class to print definitions lists. The first list
        should contain a header with parameter names, and the second list shall contain the
        corresponding set IDs"""
        return [], []
