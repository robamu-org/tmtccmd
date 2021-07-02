#!/usr/bin/python3.8
"""
@file   tmtcc_sequential_sender_receiver.py
@date   01.11.2019
@brief  Used to send multiple TCs in sequence and listen for replies after each sent TC
"""
import sys
import time

from tmtccmd.sendreceive.cmd_sender_receiver import CommandSenderReceiver
from tmtccmd.ccsds.handler import CcsdsTmHandler
from tmtccmd.sendreceive.tm_listener import TmListener
from tmtccmd.com_if.com_interface_base import CommunicationInterface
from tmtccmd.utility.tmtc_printer import TmTcPrinter
from tmtccmd.utility.logger import get_console_logger
from tmtccmd.tc.definitions import TcQueueT

LOGGER = get_console_logger()


class SequentialCommandSenderReceiver(CommandSenderReceiver):
    """Specific implementation of CommandSenderReceiver to send multiple telecommands in sequence"""
    def __init__(
            self, com_if: CommunicationInterface, tmtc_printer: TmTcPrinter, tm_handler: CcsdsTmHandler,
            apid: int, tm_listener: TmListener, tc_queue: TcQueueT):
        """
        :param com_if:          CommunicationInterface object, passed on to CommandSenderReceiver
        :param tm_listener:     TmListener object which runs in the background and receives all Telemetry
        :param tmtc_printer:    TmTcPrinter object, passed on to CommandSenderReceiver for this time period
        """
        super().__init__(
            com_if=com_if, tmtc_printer=tmtc_printer, tm_listener=tm_listener, tm_handler=tm_handler
        )
        self._apid = apid
        self._tc_queue = tc_queue
        self.__all_replies_received = False

    def send_queue_tc_and_receive_tm_sequentially(self):
        """Primary function which is called for sequential transfer.
        :return:
        """
        self._tm_listener.set_listener_mode(TmListener.ListenerModes.SEQUENCE)
        # tiny delay for pus_tm listener
        time.sleep(0.05)
        if self._tc_queue:
            try:
                # Set to true for first packet, otherwise nothing will be sent.
                self._reply_received = True
                self.__handle_tc_sending()
            except (KeyboardInterrupt, SystemExit):
                LOGGER.info("Keyboard Interrupt.")
                sys.exit()
        else:
            LOGGER.warning("Supplied TC queue is empty!")

    def __handle_tc_sending(self):
        while not self.__all_replies_received:
            while not self._tc_queue.__len__() == 0:
                self.__check_for_reply()
                self.__check_next_tc_send()
                if self._tc_queue.__len__() == 0:
                    self._start_time = time.time()
                    break
                time.sleep(0.2)
            if not self._reply_received:
                self.__check_for_reply()
                self._check_for_timeout()
            if self._reply_received:
                self.__all_replies_received = True
                break
            time.sleep(0.2)
        self._tm_listener.set_mode_op_finished()
        LOGGER.info("SequentialSenderReceiver: All replies received!")

    def __check_for_reply(self):
        if self._tm_listener.reply_event():
            self._reply_received = True
            self._tm_listener.clear_reply_event()
            packet_queue = self._tm_listener.retrieve_ccsds_tm_packet_queue(
                apid=self._apid, clear=True
            )
            self._tm_handler.handle_ccsds_packet_queue(apid=self._apid, packet_queue=packet_queue)
        # This makes reply reception more responsive
        elif self._tm_listener.tm_packets_available():
            packet_queue = self._tm_listener.retrieve_ccsds_tm_packet_queue(
                apid=self._apid, clear=True
            )
            self._tm_handler.handle_ccsds_packet_queue(apid=self._apid, packet_queue=packet_queue)

    def __check_next_tc_send(self):
        if self.wait_period_ongoing():
            return
        # this flag is set in the separate receiver thread too
        if self._reply_received:
            if self.__send_next_telecommand():
                self._reply_received = False
        # just calculate elapsed time if start time has already been set (= command has been sent)
        else:
            self._check_for_timeout()

    def __send_next_telecommand(self) -> bool:
        """Sends the next telecommand and returns whether an actual telecommand was sent"""
        tc_queue_tuple = self._tc_queue.pop()
        if self.check_queue_entry(tc_queue_tuple):
            self._start_time = time.time()
            pus_packet, pus_packet_info = tc_queue_tuple
            self._com_if.send(pus_packet)
            return True
        # queue empty.
        elif not self._tc_queue:
            # Special case: Last queue entry is not a Telecommand
            self._reply_received = True
            # Another specal case: Last queue entry is to wait.
            if self._wait_period > 0:
                self.wait_period_ongoing(True)
                self.__all_replies_received = True
            return False
        else:
            # If the queue entry was not a telecommand, send next telecommand
            self.__check_next_tc_send()
            return True
