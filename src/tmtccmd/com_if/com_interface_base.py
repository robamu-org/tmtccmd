# -*- coding: utf-8 -*-
"""
Program: tmtcc_com_interface_base.py
Date: 01.11.2019
Description: Generic Communication Interface. Defines the syntax of the communication functions.
             Abstract methods must be implemented by child class (e.g. Ethernet Com IF)

@author: R. Mueller
"""
from abc import abstractmethod
from typing import Tuple
from tmtccmd.pus_tm.factory import PusTmListT
from tmtccmd.utility.tmtc_printer import TmTcPrinter
from tmtccmd.pus_tc.base import PusTcInfoT


# pylint: disable=useless-return
# pylint: disable=no-self-use
# pylint: disable=unused-argument
class CommunicationInterface:
    """
    Generic form of a communication interface to separate communication logic from
    the underlying interface.
    """
    def __init__(self, tmtc_printer: TmTcPrinter):
        self.tmtc_printer = tmtc_printer
        self.valid = True

    @abstractmethod
    def initialize(self) -> any:
        """
        Perform initializations step which can not be done in constructor or which require
        returnvalues.
        """

    @abstractmethod
    def open(self) -> None:
        """
        Opens the communication interface to allow communication.
        @return:
        """

    @abstractmethod
    def close(self) -> None:
        """
        Closes the ComIF and releases any held resources (for example a Communication Port)
        :return:
        """

    @abstractmethod
    def send_data(self, data: bytearray):
        """
        Send data, for example a frame containing packets.
        """

    @abstractmethod
    def send_telecommand(self, tc_packet: bytearray, tc_packet_info: PusTcInfoT = None) -> None:
        """
        Send telecommands
        :param tc_packet: TC wiretapping_packet to send
        :param tc_packet_info: TC wiretapping_packet information
        :return: None for now
        """

    @abstractmethod
    def receive_telemetry(self, parameters: any = 0) -> PusTmListT:
        """
        Returns a list of packets. Most of the time,
        this will simply call the pollInterface function
        :param parameters:
        :return:
        """
        packet_list = []
        return packet_list

    @abstractmethod
    def poll_interface(self, parameters: any = 0) -> Tuple[bool, PusTmListT]:
        """
        Poll the interface and return a list of received packets
        :param parameters:
        :return: Tuple: boolean which specifies wheather a wiretapping_packet was received,
        and the wiretapping_packet list containing
        Tm packets
        """

    @abstractmethod
    def data_available(self, parameters: any) -> int:
        """
        Check whether TM data is available
        :param parameters:
        :return: 0 if no data is available, number of bytes or anything > 0 otherwise.
        """
