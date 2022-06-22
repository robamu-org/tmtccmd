"""Used to send multiple TCs in sequence and listen for replies after each sent TC"""
import sys
import time
import threading

from tmtccmd.tc.ccsds_sender_receiver import CcsdsCommandSenderReceiver
from tmtccmd.tc.handler import TcHandlerBase
from tmtccmd.tc.queue import QueueWrapper
from tmtccmd.ccsds.handler import CcsdsTmHandler
from tmtccmd.tm.ccsds_tm_listener import CcsdsTmListener
from tmtccmd.com_if.com_interface_base import CommunicationInterface
from tmtccmd.logging import get_console_logger


LOGGER = get_console_logger()


class SequentialCcsdsSenderReceiver(CcsdsCommandSenderReceiver):
    """Specific implementation of CommandSenderReceiver to send multiple telecommands in sequence"""

    def __init__(
        self,
        queue_wrapper: QueueWrapper,
        com_if: CommunicationInterface,
        tm_listener: CcsdsTmListener,
        tm_handler: CcsdsTmHandler,
        tc_handler: TcHandlerBase,
        apid: int,
    ):
        """
        :param com_if:          CommunicationInterface object, passed on to CommandSenderReceiver
        :param tm_listener:     TmListener object which runs in the background and receives
                                all Telemetry
        """
        super().__init__(
            com_if=com_if,
            tm_listener=tm_listener,
            tm_handler=tm_handler,
            apid=apid,
            tc_handler=tc_handler,
        )
        self._tc_handler = tc_handler
        self._queue_wrapper = queue_wrapper
        self.__all_replies_received = False
        # This flag can be used to notify the sender to send the next TC
        self._next_send_condition = False

        # create a daemon (which will exit automatically if all other threads are closed)
        # to handle telemetry
        # this is an optional  functionality which can be used by the TmTcHandler aka backend
        self.daemon_thread = threading.Thread(
            target=self.__perform_daemon_operation, daemon=True
        )

    @property
    def queue_wrapper(self):
        return self._queue_wrapper

    @queue_wrapper.setter
    def queue_wrapper(self, queue_wrapper: QueueWrapper):
        self._queue_wrapper = queue_wrapper

    def operation(self):
        pass

    def send_queue_tc_and_receive_tm_sequentially(self):
        """Primary function which is called for sequential transfer.
        :return:
        """
        self._tm_listener.sequence_mode()
        # tiny delay for pus_tm listener
        time.sleep(0.05)
        if self.queue_wrapper.queue:
            try:
                self.__handle_tc_sending_and_tm_reception()
            except (KeyboardInterrupt, SystemExit):
                LOGGER.info("Keyboard Interrupt.")
                sys.exit()
        else:
            LOGGER.warning("Supplied TC queue is empty!")

    def send_queue_tc_and_return(self):
        self._tm_listener.listener_mode()
        # tiny delay for pus_tm listener
        time.sleep(0.05)
        if self.queue_wrapper.queue:
            try:
                # Set to true for first packet, otherwise nothing will be sent.
                self._next_send_condition = True
                if not self.queue_wrapper.queue.__len__() == 0:
                    self.__check_next_tc_send()
            except (KeyboardInterrupt, SystemExit):
                LOGGER.info("Keyboard Interrupt.")
                sys.exit()
        else:
            LOGGER.warning("Supplied TC queue is empty!")

    def start_daemon(self):
        if not self.daemon_thread.is_alive():
            self.daemon_thread.start()

    def __perform_daemon_operation(self):
        while True:
            self.__check_for_reply()
            time.sleep(0.2)

    def __print_rem_timeout(self, op_divider: int, divisor: int = 15):
        if op_divider % divisor == 0:
            rem_time = self._wait_end - time.time()
            if rem_time > 0:
                LOGGER.info(f"{rem_time:.01f} seconds wait time remaining")

    def __handle_tc_sending_and_tm_reception(self):
        """Internal function which handles the given TC queue while also simultaneously
        polling all TM.
        TODO: Make it testable by not delaying here and removing the loop, make
              this function runnable in discrete steps
        """
        # Set to true for first packet, otherwise nothing will be sent.
        self._next_send_condition = True
        next_sleep = 0.2
        op_divider = 0
        tc_queue_is_empty_and_processed = False
        while not self.__all_replies_received:
            # Do not use continue anywhere in this while loop for now
            if not tc_queue_is_empty_and_processed:
                if self.queue_wrapper.queue.__len__() == 0:
                    if self._wait_period == 0:
                        # cache this for last wait time
                        self._start_time = time.time()
                        tc_queue_is_empty_and_processed = True
                self.__check_for_reply()
                if not tc_queue_is_empty_and_processed:
                    if not self.wait_period_ongoing():
                        self._wait_period = 0
                        self.__check_next_tc_send()
                    self.__print_rem_timeout(op_divider=op_divider)
                    time.sleep(next_sleep)
            else:
                if not self._check_for_tm_timeout():
                    self.__check_for_reply()
                    self.__print_rem_timeout(op_divider=op_divider)
                    # Delay for a bit longer in case we are waiting for the TM timeout
                    next_sleep = 0.5
                else:
                    self.__all_replies_received = True
                    break
            time.sleep(next_sleep)
            op_divider += 1
        self._tm_listener.set_mode_op_finished()
        LOGGER.info("SequentialSenderReceiver: All replies received!")

    def __check_for_reply(self):
        if self._tm_listener.reply_event():
            self._reply_received = True
            self._tm_listener.clear_reply_event()
            packet_queue = self._tm_listener.retrieve_ccsds_tm_packet_queue(
                apid=self._apid, clear=True
            )
            self._tm_handler.handle_ccsds_packet_queue(
                apid=self._apid, tm_queue=packet_queue, handler=None
            )
        # This makes reply reception more responsive
        elif self._tm_listener.tm_packets_available():
            packet_queue = self._tm_listener.retrieve_ccsds_tm_packet_queue(
                apid=self._apid, clear=True
            )
            self._tm_handler.handle_ccsds_packet_queue(
                apid=self._apid, tm_queue=packet_queue, handler=None
            )

    def __check_next_tc_send(self):
        # this flag is set in the separate receiver thread too
        if self._next_send_condition:
            if self._send_next_telecommand():
                self._next_send_condition = False
        # just calculate elapsed time if start time has already been set (= command has been sent)
        else:
            if self._check_for_tm_timeout():
                self._next_send_condition = True

    def _send_next_telecommand(self) -> bool:
        """Sends the next telecommand and returns whether an actual telecommand was sent"""
        # Queue empty. Can happen because a wait period might still be ongoing
        if not self.queue_wrapper.queue:
            return False
        if self.wait_period_ongoing():
            return False
        next_queue_entry = self.queue_wrapper.queue.pop()
        if self.check_queue_entry(next_queue_entry):
            self._start_time = time.time()
            self._tc_handler.pre_send_cb(next_queue_entry, self._com_if)

        # queue empty.
        elif not self.queue_wrapper.queue:
            # Another special case: Last queue entry is to wait.
            if self._wait_period > 0:
                if self.wait_period_ongoing():
                    return False
                self._wait_period = 0
                self.__all_replies_received = True
            return False
        else:
            self._tc_handler.pre_send_cb(next_queue_entry, self._com_if)
            # If the queue entry was not a telecommand, send next telecommand
            self.__check_next_tc_send()
            return True