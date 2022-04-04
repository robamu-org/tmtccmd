# -*- coding: utf-8 -*-
"""Generic Communication Interface. Defines the syntax of the communication functions.
Abstract methods must be implemented by child class (e.g. Ethernet Com IF)
:author:     R. Mueller
"""
from abc import abstractmethod

from tmtccmd.tm.definitions import TelemetryListT
from tmtccmd.utility.tmtc_printer import FsfwTmTcPrinter


class CommunicationInterface:
    """Generic form of a communication interface to separate communication logic from
    the underlying interface.
    """

    def __init__(self, com_if_key: str):
        self.valid = True
        self.com_if_key = com_if_key

    def get_id(self) -> str:
        return self.com_if_key

    @abstractmethod
    def initialize(self, args: any = None) -> any:
        """Perform initializations step which can not be done in constructor or which require
        returnvalues.
        """

    @abstractmethod
    def open(self, args: any = None) -> None:
        """Opens the communication interface to allow communication.

        :return:
        """

    @abstractmethod
    def close(self, args: any = None) -> None:
        """Closes the ComIF and releases any held resources (for example a Communication Port).

        :return:
        """

    @abstractmethod
    def send(self, data: bytearray):
        """Send raw data"""

    @abstractmethod
    def receive(self, parameters: any = 0) -> TelemetryListT:
        """Returns a list of received packets. The child class can use a separate thread to poll for
        the packets or use some other mechanism and container like a deque to store packets
        to be returned here.

        :param parameters:
        :return:
        """
        packet_list = []
        return packet_list

    @abstractmethod
    def data_available(self, timeout: float, parameters: any) -> int:
        """Check whether TM data is available.

        :param parameters: Can be an arbitrary parameter like a timeout
        :return: 0 if no data is available, number of bytes or anything > 0 otherwise.
        """
