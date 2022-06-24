"""Contains the TmListener which can be used to listen to Telemetry in the background"""
import sys
import time
import threading
from collections import deque
from typing import Dict, List, Tuple, Optional
from enum import Enum

from spacepackets.ccsds.spacepacket import get_apid_from_raw_space_packet
from tmtccmd.ccsds.handler import CcsdsTmHandler

from tmtccmd.tm.definitions import TelemetryQueueT, TelemetryListT, TmTypes
from tmtccmd.logging import get_console_logger
from tmtccmd.com_if.com_interface_base import CommunicationInterface
from tmtccmd.utility.conf_util import acquire_timeout

LOGGER = get_console_logger()

INVALID_APID = -2
UNKNOWN_TARGET_ID = -1
QueueDictT = Dict[int, Tuple[TelemetryQueueT, int]]
QueueListT = List[Tuple[int, TelemetryQueueT]]


class CcsdsTmListener:
    """Performs all TM listening operations.
    This listener to have a permanent means to receive data. A background thread is used
    to poll data with the provided communication interface. Dedicated sender and receiver object
    or any other software component can get the received packets from the internal deque container.
    """

    DEFAULT_MODE_OPERATION_TIMEOUT = 300.0
    DEFAULT_UNKNOWN_QUEUE_MAX_LEN = 50
    QUEUE_DICT_QUEUE_IDX = 0
    QUEUE_DICT_MAX_LEN_IDX = 1
    DEFAULT_TM_TIMEOUT = 5.0

    DEFAULT_LOCK_TIMEOUT = 0.5

    def __init__(
        self,
        com_if: CommunicationInterface,
        tm_handler: CcsdsTmHandler,
        seq_timeout: float = DEFAULT_TM_TIMEOUT,
        tm_type: TmTypes = TmTypes.CCSDS_SPACE_PACKETS,
    ):
        """Initiate a TM listener.
        :param com_if: Type of communication interface,
            e.g. a serial or ethernet interface
        :param tm_type: Telemetry type. Default to CCSDS space packets for now
        """
        self.__com_if = com_if
        self.seq_timeout = seq_timeout
        self.__tm_type = tm_type
        self.__tm_handler = tm_handler

    @property
    def com_if(self):
        return self.__com_if

    @com_if.setter
    def com_if(self, com_if: CommunicationInterface):
        self.__com_if = com_if

    def operation(self):
        packet_list = self.__com_if.receive()
        for tm_packet in packet_list:
            if self.__tm_type == TmTypes.CCSDS_SPACE_PACKETS:
                packet_handled = self.__handle_ccsds_space_packet(tm_packet=tm_packet)
                if packet_handled:
                    continue

    def __handle_ccsds_space_packet(self, tm_packet: bytes) -> bool:
        if len(tm_packet) < 6:
            LOGGER.warning("TM packet to small to be a CCSDS space packet")
        else:
            apid = get_apid_from_raw_space_packet(tm_packet)
            return self.__tm_handler.handle_packet(apid, tm_packet)
        return False
