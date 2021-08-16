from tmtccmd.ccsds.log import LOGGER


class CfdpLv:
    def __init__(self, serialize: bool, value: bytearray = None):
        """This class encapsulates CFDP LV fields
        :raise ValueError: If value is invalid and serilization is enabled or if length of bytearray
        is too large
        :param serialize:
        :param value:
        """
        if serialize and value is None:
            LOGGER.warning('All parameter have to be valid for serialization')
            raise ValueError
        if len > 255:
            LOGGER.warning('Length too large for LV field')
            raise ValueError
        self.len = len(value)
        self.value = value

    def pack(self):
        packet = bytearray()
        packet.append(self.len)
        packet.extend(self.value)

    def unpack(self, raw_bytes: bytearray):
        """Parses LV field at the start of the given bytearray
        :raise ValueError: Invalid lenght found
        """
        self.len = raw_bytes[0]
        if self.len > 255:
            LOGGER.warning('Length too large for LV field')
            raise ValueError
        elif self.len > 0:
            self.value = raw_bytes[1: 1 + self.len]
