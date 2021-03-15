"""
@file   tmtcc_pus_tc_base.py
@brief  This module contains the PUS telemetry class representation to
        deserialize raw PUS telemetry packets.
@author R. Mueller
"""
import sys
from enum import Enum
from typing import Dict, Union, Tuple, Deque

from tmtccmd.core.definitions import QueueCommands, CoreGlobalIds
from tmtccmd.utility.tmtcc_logger import get_logger

LOGGER = get_logger()

try:
    import crcmod
except ImportError:
    LOGGER.error("crcmod package not installed!")
    sys.exit(1)


class TcDictionaryKeys(Enum):
    """ Keys for telecommand dictionary """
    SERVICE = 1
    SUBSERVICE = 2
    SSC = 3
    PACKET_ID = 4
    DATA = 5


PusTcInfo = Dict[TcDictionaryKeys, any]
PusTcInfoT = Union[PusTcInfo, None]
PusTcTupleT = Tuple[bytearray, PusTcInfoT]
TcAuxiliaryTupleT = Tuple[QueueCommands, any]
TcQueueEntryT = Union[TcAuxiliaryTupleT, PusTcTupleT]
TcQueueT = Deque[TcQueueEntryT]
PusTcInfoQueueT = Deque[PusTcInfoT]


# pylint: disable=too-many-instance-attributes
# pylint: disable=too-many-arguments
class PusTelecommand:
    """
    @brief  Class representation of a PUS telecommand.
    @details
    It can be used to pack a raw telecommand from
    input parameters. The structure of a PUS telecommand is specified in ECSS-E-70-41A on p.42
    and is also shown below (bottom)
    """
    HEADER_SIZE = 6
    # This is the current size of a telecommand without application data. Consists of
    # the 6 byte packet header, 4 byte data field header (1 byte source ID) and 2 byte CRC.
    CURRENT_NON_APP_DATA_SIZE = 10

    def __init__(self, service: int, subservice: int, ssc=0, app_data: bytearray = bytearray([]),
                 source_id: int = 0, version: int = 0, apid: int = -1):
        # To get the correct globally configured APID
        if apid == -1:
            from tmtccmd.core.globals_manager import get_global
            apid = get_global(CoreGlobalIds.APID)
        """
        Initiates a telecommand with the given parameters.
        """
        packet_type = 1
        data_field_header_flag = 1
        self.packet_id_bytes = [0x0, 0x0]
        self.packet_id_bytes[0] = \
            ((version << 5) & 0xE0) | ((packet_type & 0x01) << 4) | \
            ((data_field_header_flag & 0x01) << 3) | ((apid & 0x700) >> 8)
        self.packet_id_bytes[1] = apid & 0xFF
        self.packet_id = (self.packet_id_bytes[0] << 8) | self.packet_id_bytes[1]
        self.ssc = ssc
        self.psc = (ssc & 0x3FFF) | (0xC0 << 8)
        self.pus_version_and_ack_byte = 0b0001_1111
        self.service = service
        self.subservice = subservice
        self.source_id = source_id
        self.app_data = app_data

    def __repr__(self):
        """
        Returns the representation of a class instance.
        TODO: Maybe a custom ID or dict consisting of SSC, Service and Subservice would be better.
        """
        return self.ssc

    def __str__(self):
        """
        Returns string representation of a class instance.
        """
        return "TC[" + str(self.service) + "," + str(self.subservice) + "] " + " with SSC " + \
               str(self.ssc)

    def get_data_length(self) -> int:
        """
        Retrieve size of TC packet in bytes.
        Formula according to PUS Standard: C = (Number of octets in packet data field) - 1.
        The size of the TC packet is the size of the packet secondary header with
        source ID + the length of the application data + length of the CRC16 checksum - 1
        """
        try:
            data_length = 4 + len(self.app_data) + 1
            return data_length
        except TypeError:
            LOGGER.error("PusTelecommand: Invalid type of application data!")
            return 0

    def get_total_length(self):
        """
        Length of full packet in bytes.
        The header length is 6 bytes and the data length + 1 is the size of the data field.
        """
        return self.get_data_length() + PusTelecommand.HEADER_SIZE + 1

    def pack(self) -> bytearray:
        """
        Serializes the TC data fields into a bytearray.
        """
        data_to_pack = bytearray()
        data_to_pack.append(self.packet_id_bytes[0])
        data_to_pack.append(self.packet_id_bytes[1])
        data_to_pack.append((self.psc & 0xFF00) >> 8)
        data_to_pack.append(self.psc & 0xFF)
        length = self.get_data_length()
        data_to_pack.append((length & 0xFF00) >> 8)
        data_to_pack.append(length & 0xFF)
        data_to_pack.append(self.pus_version_and_ack_byte)
        data_to_pack.append(self.service)
        data_to_pack.append(self.subservice)
        data_to_pack.append(self.source_id)
        data_to_pack += self.app_data
        crc_func = crcmod.mkCrcFun(0x11021, rev=False, initCrc=0xFFFF, xorOut=0x0000)
        crc = crc_func(data_to_pack)

        data_to_pack.append((crc & 0xFF00) >> 8)
        data_to_pack.append(crc & 0xFF)
        return data_to_pack

    def pack_information(self) -> PusTcInfoT:
        """
        Packs TM information into a dictionary.
        """
        tc_information = {
            TcDictionaryKeys.SERVICE: self.service,
            TcDictionaryKeys.SUBSERVICE: self.subservice,
            TcDictionaryKeys.SSC: self.ssc,
            TcDictionaryKeys.PACKET_ID: self.packet_id,
            TcDictionaryKeys.DATA: self.app_data
        }
        return tc_information

    def pack_command_tuple(self) -> PusTcTupleT:
        """ Pack a tuple consisting of the raw packet and an information dictionary """
        command_tuple = (self.pack(), self.pack_information())
        return command_tuple

    def print(self):
        """ Print the raw command in a clean format. """
        packet = self.pack()
        print("Command in Hexadecimal: [", end="")
        for counter in range(len(packet)):
            if counter == len(packet) - 1:
                print(str(hex(packet[counter])), end="")
            else:
                print(str(hex(packet[counter])) + ", ", end="")
        print("]")


def generate_packet_crc(tc_packet: bytearray) -> bytearray:
    """
    Removes current Packet Error Control, calculates new
    CRC16 checksum and adds it as correct Packet Error Control Code.
    Reference: ECSS-E70-41A p. 207-212
    """
    crc_func = crcmod.mkCrcFun(0x11021, rev=False, initCrc=0xFFFF, xorOut=0x0000)
    crc = crc_func(bytearray(tc_packet[0:len(tc_packet) - 2]))
    tc_packet[len(tc_packet) - 2] = (crc & 0xFF00) >> 8
    tc_packet[len(tc_packet) - 1] = crc & 0xFF
    return tc_packet


def generate_crc(data: bytearray) -> bytearray:
    """
    Takes the application data, appends the CRC16 checksum and returns resulting bytearray
    """
    data_with_crc = bytearray()
    data_with_crc += data
    crc_func = crcmod.mkCrcFun(0x11021, rev=False, initCrc=0xFFFF, xorOut=0x0000)
    crc = crc_func(data)
    data_with_crc.append((crc & 0xFF00) >> 8)
    data_with_crc.append(crc & 0xFF)
    return data_with_crc

# pylint: disable=line-too-long

# Structure of a PUS TC Packet :
# A PUS wiretapping_packet consists of consecutive bits, the allocation and structure is standardised.
# Extended information can be found in ECSS-E-70-41A  on p.42
# The easiest form to send a PUS Packet is in hexadecimal form.
# A two digit hexadecimal number equals one byte, 8 bits or one octet
# o = optional, Srv = Service
#
# The structure is shown as follows for TC[17,1]
# 1. Structure Header
# 2. Structure Subheader
# 3. Component (size in bits)
# 4. Hexadecimal number
# 5. Binary Number
# 6. Decimal Number
#
# -------------------------------------------Packet Header(48)------------------------------------------|   Packet   |
#  ----------------Packet ID(16)----------------------|Packet Sequence Control (16)| Packet Length (16) | Data Field |
# Version       | Type(1) |Data Field    |APID(11)    | SequenceFlags(2) |Sequence |                    | (Variable) |
# Number(3)     |         |Header Flag(1)|            |                  |Count(14)|                    |            |
#           0x18               |    0x73              |       0xc0       | 0x19    |   0x00  |   0x04   |            |
#    000      1      1      000|  01110011            | 11  000000       | 00011001|00000000 | 0000100  |            |
#     0   |   1   |  1     |    115(ASCII s)          | 3 |            25          |   0     |    4     |            |
#
#   - Packet Length is an unsigned integer C = Number of Octets in Packet Data Field - 1
#
# Packet Data Field Structure:
#
# ------------------------------------------------Packet Data Field------------------------------------------------- |
# ---------------------------------Data Field Header ---------------------------|AppData|Spare|    PacketErrCtr      |
# CCSDS(1)|TC PUS Ver.(3)|Ack(4)|SrvType (8)|SrvSubtype(8)|Source ID(o)|Spare(o)|  (var)|(var)|         (16)         |
#        0x11 (0x1F)            |  0x11     |   0x01      |            |        |       |     | 0xA0     |    0xB8   |
#    0     001     1111         |00010001   | 00000001    |            |        |       |     |          |           |
#    0      1       1111        |    17     |     1       |            |        |       |     |          |           |
#
#   - The source ID is present as one byte. For now, ground = 0x00.
