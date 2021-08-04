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
    """Encapsulates the CFDP TLV (type-lenght-value) format.
    For more information, refer to CCSDS 727.0-B-5 p.77
    """
    def __init__(
            self, serialize: bool, type: TlvTypes = None, length: int = None,
            value: bytearray = None
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
        if serialize:
            if type is None or length is None or value is None:
                LOGGER.warning('All parameter have to be valid for serialization')
                raise ValueError
            if length > 255 or length < 0:
                raise ValueError
            if len(value) != length:
                raise ValueError
        self.type = type
        self.length = length
        self.value = value

    def pack(self):
        tlv_data = bytearray()
        tlv_data.append(self.type)
        tlv_data.append(self.length)
        tlv_data.extend(self.value)

    def unpack(self, raw_bytes: bytearray):
        """Unpack a TLV field from a raw bytearray
        :param raw_bytes:
        :raise ValueError: Invalid format of the raw bytearray or type field invalid
        :return:
        """
        if len(raw_bytes) < 2:
            LOGGER.warning('Invalid length for TLV field, less than 2')
            raise ValueError
        try:
            self.type = TlvTypes(raw_bytes[0])
        except ValueError:
            LOGGER.warning(
                f'TLV field invalid, found value {self.type} is not a possible TLV parameter'
            )
            raise ValueError
        self.length = raw_bytes[1]
        if len(raw_bytes) > 2:
            self.value = raw_bytes[2:]