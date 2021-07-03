"""
Used to send multiple TCs as bursts and listen for replies simultaneously. Used by Module Tester
"""
import sys
import time
from typing import Union, Deque
from collections import deque

from tmtccmd.config.definitions import CoreGlobalIds
from tmtccmd.sendreceive.sequential_sender_receiver import SequentialCommandSenderReceiver
from tmtccmd.com_if.com_interface_base import CommunicationInterface
from tmtccmd.utility.tmtc_printer import TmTcPrinter
from tmtccmd.core.globals_manager import get_global
from tmtccmd.sendreceive.tm_listener import TmListener
from tmtccmd.utility.tmtc_printer import get_console_logger


LOGGER = get_console_logger()


class MultipleCommandSenderReceiver(SequentialCommandSenderReceiver):
    """Difference to seqential sender: This class can send TCs in bursts.
    Wait intervals can be specified with wait time between the send bursts.
    This is generally done in the separate test classes in UnitTest
    """
    def __init__(self, com_if: CommunicationInterface, tmtc_printer: TmTcPrinter,
                 tc_queue: Deque, tm_listener: TmListener, wait_intervals: list,
                 wait_time: Union[float, list], print_tm: bool):
        """TCs are sent in burst when applicable. Wait intervals can be specified by supplying respective arguments
        :param com_if:
        :param tmtc_printer:
        :param tc_queue:
        :param wait_intervals: List of pause intervals. For example [1,3] means that a wait_time
            is applied after
        sendinf the first and the third telecommand
        :param wait_time: List of wait times or uniform wait time as float
        :param print_tm:
        """
        super().__init__(com_if=com_if, tmtc_printer=tmtc_printer,
                         tm_listener=tm_listener, tc_queue=tc_queue)
        self.waitIntervals = wait_intervals
        self.waitTime = wait_time
        self.printTm = print_tm
        self.tm_packet_queue = deque()
        self.tc_info_queue = deque()
        self.pusPacketInfo = []
        self.pusPacket = []
        self.waitCounter = 0

    def send_tc_queue_and_return_info(self):
        try:
            self._tm_listener.set_listener_mode(TmListener.ListenerModes.MANUAL)
            self._tm_listener.event_mode_change.set()
            time.sleep(0.1)
            # TC info queue is set in this function
            self.__send_all_queue()
            time.sleep(self._tm_timeout / 1.4)
            # Get a copy of the queue, otherwise we will lose the data.
            tm_packet_queue_list = self._tm_listener.retrieve_tm_packet_queue().copy()
            if get_global(CoreGlobalIds.PRINT_TM):
                self.print_tm_queue(self._tm_listener.retrieve_tm_packet_queue())
            self._tm_listener.clear_tm_packet_queue()
            if get_global(CoreGlobalIds.PRINT_TO_FILE):
                self._tmtc_printer.print_to_file()
            return self.tc_info_queue, tm_packet_queue_list
        except (KeyboardInterrupt, SystemExit):
            LOGGER.info("Keyboard Interrupt.")
            sys.exit()

    def __handle_tc_resending(self):
        while not self.__all_replies_received:
            if self._tc_queue.__len__ == 0:
                if self._start_time == 0:
                    self._start_time = time.time()
            self._check_for_timeout()

    def __send_all_queue(self):
        while not self._tc_queue.__len__() == 0:
            self.__send_and_print_tc()

    def __send_and_print_tc(self):
        tc_queue_tuple = self._tc_queue.pop()
        if self.check_queue_entry(tc_queue_tuple):
            pus_packet, pus_packet_obj = tc_queue_tuple
            self.tc_info_queue.append(pus_packet_obj)
            self._com_if.send_telecommand(pus_packet, pus_packet_obj)
            self.__handle_waiting()

    def __handle_waiting(self):
        self.waitCounter = self.waitCounter + 1
        if self.waitCounter in self.waitIntervals:
            if isinstance(self.waitTime, list):
                time.sleep(self.waitTime[self.waitIntervals.index(self.waitCounter)])
            else:
                time.sleep(self.waitTime)
        if self.waitTime == 0:
            # To prevent thread starvation
            time.sleep(0.1)

    def __retrieve_listener_tm_packet_queue(self):
        if self._tm_listener.reply_event():
            return self._tm_listener.retrieve_tm_packet_queue()
        else:
            LOGGER.error("Multiple Command SenderReceiver: Configuration error, "
                         "reply event not set in TM listener")

    def __clear_listener_tm_info_queue(self):
        self._tm_listener.clear_tm_packet_queue()
