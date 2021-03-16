"""
This module creates the class required to generate PUS telemetry packets.
"""
import crcmod

from tmtccmd.pus_tm.base import PusTelemetry, PusTelemetryTimestamp
from tmtccmd.utility.tmtcc_logger import get_logger


LOGGER = get_logger()


# pylint: disable=too-many-instance-attributes
# pylint: disable=too-many-arguments
class PusTelemetryCreator:
    """
    Alternative way to create a PUS Telemetry packet by specifying telemetry parameters,
    similarly to the way telecommands are created. This can be used to create telemetry
    directly in the software. See documentation and more information related to
    the ESA PUS standard in the PusTelemetry documentation.
    """
    def __init__(self, service: int, subservice: int, ssc: int = 0,
                 source_data: bytearray = bytearray([]), apid: int = 0x73, version: int = 0):
        """
        Initiates the unserialized data fields for the PUS telemetry packet.
        """
        # packet type for telemetry is 0 as specified in standard
        packet_type = 0
        # specified in standard
        data_field_header_flag = 1
        self.packet_id_bytes = [0x0, 0x0]
        self.packet_id_bytes[0] = \
            ((version << 5) & 0xE0) | ((packet_type & 0x01) << 4) | \
            ((data_field_header_flag & 0x01) << 3) | ((apid & 0x700) >> 8)
        self.packet_id_bytes[1] = apid & 0xFF
        self.packet_id = (self.packet_id_bytes[0] << 8) | self.packet_id_bytes[1]
        self.ssc = ssc
        self.psc = (ssc & 0x3FFF) | (0xC0 << 8)
        self.pus_version_and_ack_byte = 0b00011111

        # NOTE: In PUS-C, the PUS Version is 2 and specified for the first 4 bits.
        # The other 4 bits of the first byte are the spacecraft time reference status
        # To change to PUS-C, set 0b00100000
        self.data_field_version = 0b00010000
        self.service = service
        self.subservice = subservice
        self.pack_subcounter = 0
        # it is assumed the time field consts of 8 bytes.

        self.source_data = source_data

    def print(self):
        """ Print the raw command in a clean format. """
        packet = self.pack()
        print_out = "Telemetry in Hexadecimal: ["
        for counter in range(len(packet)):
            if counter == len(packet) - 1:
                print_out += str(hex(packet[counter]))
            else:
                print_out += str(hex(packet[counter])) + ", "
        print_out += "]"
        LOGGER.info(print_out)

    def pack(self) -> bytearray:
        """
        Serializes the PUS telemetry into a raw packet.
        """
        tm_packet_raw = bytearray()
        # PUS Header
        tm_packet_raw.extend(self.packet_id_bytes)
        tm_packet_raw.append((self.psc & 0xFF00) >> 8)
        tm_packet_raw.append(self.psc & 0xFF)
        source_length = self.get_source_data_length()
        tm_packet_raw.append((source_length & 0xFF00) >> 8)
        tm_packet_raw.append(source_length & 0xFF)
        # PUS Source Data Field
        tm_packet_raw.append(self.data_field_version)
        tm_packet_raw.append(self.service)
        tm_packet_raw.append(self.subservice)
        tm_packet_raw.append(self.pack_subcounter)
        tm_packet_raw.extend(PusTelemetryTimestamp.pack_current_time())
        # Source Data
        tm_packet_raw.extend(self.source_data)
        # CRC16 checksum
        crc_func = crcmod.mkCrcFun(0x11021, rev=False, initCrc=0xFFFF, xorOut=0x0000)
        crc16 = crc_func(tm_packet_raw)
        tm_packet_raw.append((crc16 & 0xFF00) >> 8)
        tm_packet_raw.append(crc16 & 0xFF)
        return tm_packet_raw

    def get_source_data_length(self) -> int:
        """
        Retrieve size of TM packet data header in bytes.
        Formula according to PUS Standard: C = (Number of octets in packet source data field) - 1.
        The size of the TM packet is the size of the packet secondary header with
        the timestamp + the length of the application data + PUS timestamp size +
        length of the CRC16 checksum - 1
        """
        try:
            data_length = 4 + PusTelemetry.PUS_TIMESTAMP_SIZE + len(self.source_data) + 1
            return data_length
        except TypeError:
            LOGGER.error("PusTelecommand: Invalid type of application data!")
            return 0
