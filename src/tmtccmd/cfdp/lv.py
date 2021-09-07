from __future__ import annotations
from tmtccmd.ccsds.log import LOGGER


class CfdpLv:
    def __init__(self, value: bytearray):
        """This class encapsulates CFDP LV fields
        :raise ValueError: If value is invalid and serilization is enabled or if length of bytearray
        is too large
        :param serialize:
        :param value:
        """
        if len(value) > 255:
            LOGGER.warning('Length too large for LV field')
            raise ValueError
        self.len = len(value)
        self.value = value

    def get_len(self):
        """Returns length of full LV packet"""
        return self.len + 1

    def pack(self):
        packet = bytearray()
        packet.append(self.len)
        packet.extend(self.value)

    @classmethod
    def unpack(cls, raw_bytes: bytearray) -> CfdpLv:
        """Parses LV field at the start of the given bytearray
        :raise ValueError: Invalid length found
        """
        detected_len = raw_bytes[0]
        if detected_len > 255:
            LOGGER.warning('Length too large for LV field')
            raise ValueError
        return cls(
            value=raw_bytes[1:]
        )
