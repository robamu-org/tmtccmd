from __future__ import annotations
import enum
from tmtccmd.ccsds.log import LOGGER


class TlvTypes(enum.IntEnum):
    FILESTORE_REQUEST = 0x00
    FILESTORE_RESPONSE = 0x01
    MESSAGE_TO_USER = 0x02
    FAULT_HANDLER = 0x04
    FLOW_LABEL = 0x05
    ENTITY_ID = 0x06


class CfdpTlv:
    MINIMAL_LEN = 2

    """Encapsulates the CFDP TLV (type-lenght-value) format.
    For more information, refer to CCSDS 727.0-B-5 p.77
    """
    def __init__(
            self,
            type: TlvTypes,
            length: int,
            value: bytearray
    ):
        """Constructor for TLV field.
        :param serialize: Specfiy whether a packet is serialized or deserialized. For serialize,
        all input parameter have to be valid. For deserialization, the parameter do not have
        to be specified
        :param type:
        :param length:
        :param value:
        :raise ValueError: Length invalid or value length not equal to specified length
        """
        if length > 255 or length < 0:
            raise ValueError
        if len(value) != length:
            raise ValueError
        self.type = type
        self.length = length
        self.value = value

    def pack(self) -> bytearray:
        tlv_data = bytearray()
        tlv_data.append(self.type)
        tlv_data.append(self.length)
        tlv_data.extend(self.value)
        return tlv_data

    @classmethod
    def unpack(cls, raw_bytes: bytearray) -> CfdpTlv:
        """Parses LV field at the start of the given bytearray
        :param raw_bytes:
        :raise ValueError: Invalid format of the raw bytearray or type field invalid
        :return:
        """
        if len(raw_bytes) < 2:
            LOGGER.warning('Invalid length for TLV field, less than 2')
            raise ValueError
        try:
            type = TlvTypes(raw_bytes[0])
        except ValueError:
            LOGGER.warning(
                f'TLV field invalid, found value {type} is not a possible TLV parameter'
            )
            raise ValueError
        value = bytearray()
        if len(raw_bytes) > 2:
            value.extend(raw_bytes[2:])
        return cls(
            type=raw_bytes[0],
            length=raw_bytes[1],
            value=value
        )

    def get_total_length(self) -> int:
        return self.MINIMAL_LEN + len(self.value)
