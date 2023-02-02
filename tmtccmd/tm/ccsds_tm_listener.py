"""Contains the TmListener which can be used to listen to Telemetry in the background"""
from typing import Dict, List, Tuple

from spacepackets.ccsds.spacepacket import get_apid_from_raw_space_packet

from tmtccmd.tm import TelemetryQueueT, CcsdsTmHandler
from tmtccmd.com import ComInterface


INVALID_APID = -2
UNKNOWN_TARGET_ID = -1
QueueDictT = Dict[int, Tuple[TelemetryQueueT, int]]
QueueListT = List[Tuple[int, TelemetryQueueT]]


class PacketsTooSmallForCcsds(Exception):
    def __init__(self, packets: List[bytes]):
        self.packets = packets


class CcsdsTmListener:
    """Simple helper object which can be used for retrieving and routing CCSDS packets.
    It can be used to poll CCSDS packets from a provided :py:class:`tmtccmd.com_if.ComInterface`
    and then route them using a provided CCSDS TM handler.
    """

    def __init__(
        self,
        tm_handler: CcsdsTmHandler,
    ):
        """Initiate a TM listener.

        :param tm_handler: If valid CCSDS packets are found, they are dispatched to
            the passed handler
        """
        self.__tm_handler = tm_handler

    def operation(self, com_if: ComInterface) -> int:
        """Core operation to route packet to the provided handler.

        :param com_if:
        :raises PacketsTooSmallForCcsds: If any of the received packets are too small.
            The internal handler will still continue to process the remaining packet list retrieved
            from the COM interface.
        :return:
        """
        packet_list = com_if.receive()
        for tm_packet in packet_list:
            self.__handle_ccsds_space_packet(tm_packet)
        return len(packet_list)

    def __handle_ccsds_space_packet(self, tm_packet: bytes):
        invalid_packets = []
        if len(tm_packet) < 6:
            invalid_packets.append(tm_packet)
        else:
            apid = get_apid_from_raw_space_packet(tm_packet)
            self.__tm_handler.handle_packet(apid, tm_packet)
            return True
        if len(invalid_packets) > 0:
            raise PacketsTooSmallForCcsds(invalid_packets)
