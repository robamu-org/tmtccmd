"""
@file       tmtcc_tm_listener.py
@date       01.11.2019
@brief      Separate class to listen to telecommands.
@author     R. Mueller
"""
import sys
import time
import threading
from collections import deque
from enum import Enum

from tmtccmd.utility.logger import get_logger
from tmtccmd.com_if.com_interface_base import CommunicationInterface
from tmtccmd.pus_tm.factory import TelemetryQueueT

LOGGER = get_logger()


class TmListener:
    """Performs all TM listening operations.
    This listener to have a permanent means to receive data. A background thread is used
    to poll data with the provided communication interface. Dedicated sender and receiver object
    or any other software component can get the received packets from the internal deque container.
    """
    MODE_OPERATION_TIMEOUT = 300

    class ListenerModes(Enum):
        MANUAL = 1,
        LISTENER = 2,
        SEQUENCE = 3,

    def __init__(
            self, com_if: CommunicationInterface, tm_timeout: float, tc_timeout_factor: float
    ):
        """Initiate a TM listener
        :param com_if:              Type of communication interface, e.g. a serial or ethernet interface
        :param tm_timeout:          Timeout for the TM reception
        :param tc_timeout_factor:
        """
        self.__tm_timeout = tm_timeout
        self.tc_timeout_factor = tc_timeout_factor
        self.__com_if = com_if
        # TM Listener operations can be suspended by setting this flag
        self.event_listener_active = threading.Event()
        self.listener_active = False

        # I don't think a listener is useful without the main program,
        # so we might just declare it daemonic.
        self.listener_thread = threading.Thread(target=self.__perform_operation, daemon=True)
        self.lock_listener = threading.Lock()
        # This Event is set by sender objects to perform mode operations
        self.event_mode_change = threading.Event()
        # This Event is set and cleared by the listener to inform the sender objects
        # if a reply has been received
        self.__event_reply_received = threading.Event()
        # This Event is set by sender objects if all necessary operations are done
        # to transition back to listener mode
        self.event_mode_op_finished = threading.Event()
        # maybe we will just make the thread daemonic...
        # self.terminationEvent = threading.Event()

        self.__listener_mode = self.ListenerModes.LISTENER
        self.__tm_packet_queue = deque()

    def start(self):
        if not self.event_listener_active.is_set():
            self.event_listener_active.set()
            if not self.listener_thread.is_alive():
                self.listener_thread.start()
        else:
            LOGGER.warning("TM listener is already active!")

    def stop(self):
        self.event_listener_active.clear()

    def set_com_if(self, com_if: CommunicationInterface):
        self.__com_if = com_if

    def is_listener_active(self) -> bool:
        return self.listener_active

    def set_timeouts(self, tm_timeout):
        self.__tm_timeout = tm_timeout

    def set_listener_mode(self, listener_mode: ListenerModes):
        if listener_mode != self.__listener_mode:
            self.event_mode_change.set()
        self.__listener_mode = listener_mode

    def reply_event(self):
        if self.__event_reply_received.is_set():
            return True
        else:
            return False

    def clear_reply_event(self):
        self.__event_reply_received.clear()

    def tm_received(self):
        """This function is used to check whether any data has been received"""
        if self.__tm_packet_queue.__len__() > 0:
            return True
        else:
            return False

    def tm_packets_available(self):
        if self.lock_listener.acquire(True, timeout=1):
            if self.__tm_packet_queue:
                self.lock_listener.release()
                return True
            self.lock_listener.release()
        else:
            LOGGER.warning("TmListener: Blocked on lock acquisition for longer than 1 second!")
        return False

    def retrieve_tm_packet_queue(self) -> TelemetryQueueT:
        # We make sure that the queue is not manipulated while it is being copied.
        if self.lock_listener.acquire(True, timeout=1):
            tm_queue_copy = self.__tm_packet_queue.copy()
            self.lock_listener.release()
        else:
            tm_queue_copy = self.__tm_packet_queue.copy()
            LOGGER.warning("TmListener: Blocked on lock acquisition for longer than 1 second!")
        return tm_queue_copy

    def clear_tm_packet_queue(self):
        self.__tm_packet_queue.clear()

    def check_for_one_telemetry_sequence(self) -> bool:
        """
        @brief  Receive all telemetry for a specified time period.
        @details
        This function prints the telemetry sequence but does not return it.
        :return:
        """
        data_available = self.__com_if.data_available(self.__tm_timeout)
        if data_available == 0:
            return False
        elif data_available > 0:
            self.__read_telemetry_sequence()
            return True
        else:
            LOGGER.error("TmListener: Configuration error in communication interface!")
            sys.exit()

    def __perform_operation(self):
        while True:
            # This is running in a daemon thread so it will stop automatically if all other threads have closed
            if self.event_listener_active.is_set():
                self.listener_active = True
                self.__default_operation()
            else:
                self.listener_active = False
                # Check every 300 ms whether connection is up again.
                time.sleep(0.3)

    def __default_operation(self):
        """
        Core function. Normally, polls all packets
        """
        self.__perform_core_operation()
        if self.event_mode_change.is_set():
            self.event_mode_change.clear()
            start_time = time.time()
            while not self.event_mode_op_finished.is_set():
                elapsed_time = time.time() - start_time
                if elapsed_time < TmListener.MODE_OPERATION_TIMEOUT:
                    self.__perform_mode_operation()
                else:
                    LOGGER.warning("TmListener: Mode operation timeout occured!")
                    break
            self.event_mode_op_finished.clear()
            LOGGER.info("TmListener: Transitioning to listener mode.")
            self.__listener_mode = self.ListenerModes.LISTENER

    def __perform_core_operation(self):
        """
        The core operation listens for packets.
        """
        packet_list = self.__com_if.receive()
        if len(packet_list) > 0:
            self.__event_reply_received.set()
            # deque is thread-safe for append and pops from opposite sides but I am not sure copy
            # is so we still use a lock here.
            if self.lock_listener.acquire(blocking=True, timeout=1.0):
                self.__tm_packet_queue.appendleft(packet_list)
                self.lock_listener.release()
            else:
                LOGGER.warning("TmListener: Blocked on lock acquisition for longer than 1 second!")
        else:
            time.sleep(0.4)

    def __perform_mode_operation(self):
        """
        By setting the modeChangeEvent with set() and specifying the mode variable,
        the TmListener is instructed to perform certain operations.
        :return:
        """
        # Listener Mode
        if self.__listener_mode == self.ListenerModes.LISTENER:
            self.event_mode_op_finished.set()
        # Single Command Mode
        elif self.__listener_mode == self.ListenerModes.SEQUENCE:
            # Listen for one reply sequence.
            if self.check_for_one_telemetry_sequence():
                # Set reply event, will be cleared by checkForFirstReply()
                self.__event_reply_received.set()
            time.sleep(0.2)
        elif self.__listener_mode == self.ListenerModes.MANUAL:
            self.__perform_core_operation()

    def __read_telemetry_sequence(self):
        """Thread-safe implementation for reading a telemetry sequence."""
        start_time = time.time()
        elapsed_time = 0
        # LOGGER.info(f"TmListener: Listening for {self.__tm_timeout} seconds")
        while elapsed_time < self.__tm_timeout:
            packets_available = self.__com_if.data_available(0.2)
            if packets_available > 0:
                tm_list = self.__com_if.receive()
                # deque should be thread-safe to appends and pops from opposite sides, but
                # I am not sure about the copy operation.
                if self.lock_listener.acquire(True, timeout=1):
                    self.__tm_packet_queue.appendleft(tm_list)
                    self.lock_listener.release()
                else:
                    LOGGER.warning("TmListener: Blocked on lock acquisition for longer "
                                   "than 1 second!")
            elapsed_time = time.time() - start_time
            time.sleep(0.05)
        # the timeout value can be set by special TC queue entries if wiretapping_packet handling
        # takes longer, but it is reset here to the global value
        from tmtccmd.core.globals_manager import get_global
        from tmtccmd.config.definitions import CoreGlobalIds
        if self.__tm_timeout is not get_global(CoreGlobalIds.TM_TIMEOUT):
            self.__tm_timeout = get_global(CoreGlobalIds.TM_TIMEOUT)
        return True
