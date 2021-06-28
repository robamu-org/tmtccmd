from typing import Tuple, List
import enum

from tmtccmd.ecss.tm import PusTelemetry


class HkContentType(enum.Enum):
    HK = enum.auto()
    DEFINITIONS = enum.auto()


class Service3Base(PusTelemetry):
    """Base class. The TMTC core provides a Service 3 implementation which is intended to be used
    with the FSFW. However, users can define an own Service 3 implementation.

    The TMTC printer utility uses the fields defined in this base class to perform prinouts so
    if a custom class is defined, the user should implement this class and fill the fields
    in the TM handling hook if printout of the HK field and validity checking is desired.
    """
    def __init__(self, raw_telemetry: bytearray, custom_hk_handling: bool = False):
        super().__init__(raw_telemetry)
        self._object_id_bytes = bytearray()
        self._object_id = 0
        self._set_id = 0
        self._custom_hk_handling = custom_hk_handling

    def get_object_id(self) -> int:
        return self._object_id

    def get_object_id_bytes(self) -> bytes:
        return self._object_id_bytes

    def get_set_id(self) -> int:
        return self._set_id

    def has_custom_hk_handling(self) -> bool:
        return self._custom_hk_handling

    def get_hk_definitions_list(self) -> Tuple[List, List]:
        """Can be implemented by a child class to print definitions lists. The first list
        should contain a header with parameter names, and the second list shall contain the
        corresponding set IDs"""
        return [], []
