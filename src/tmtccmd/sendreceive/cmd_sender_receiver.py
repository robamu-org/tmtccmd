"""Base class for sender/receiver objects
@author: R. Mueller
"""
import time
from typing import Optional, Tuple
from tmtccmd.com_if.com_interface_base import CommunicationInterface
from tmtccmd.config.definitions import QueueCommands, CoreGlobalIds, UsrSendCbT
from tmtccmd.logging import get_console_logger

from tmtccmd.ccsds.handler import CcsdsTmHandler
from tmtccmd.sendreceive.tm_listener import TmListener
from tmtccmd.tc.definitions import TcQueueEntryT
from tmtccmd.core.globals_manager import get_global

LOGGER = get_console_logger()


class CommandSenderReceiver:
    """
    This is the generic CommandSenderReceiver object. All TMTC objects inherit this object,
    for example specific implementations (e.g. SingleCommandSenderReceiver)
    """

    def __init__(
        self,
        com_if: CommunicationInterface,
        tm_listener: TmListener,
        tm_handler: CcsdsTmHandler,
        apid: int,
        usr_send_wrapper: Optional[Tuple[UsrSendCbT, any]] = None,
    ):

        """
        :param com_if: CommunicationInterface object. Instantiate the desired one
        and pass it here
        """
        self._tm_timeout = get_global(CoreGlobalIds.TM_TIMEOUT)
        self._tm_handler = tm_handler
        self._tc_send_timeout_factor = get_global(CoreGlobalIds.TC_SEND_TIMEOUT_FACTOR)
        self._apid = apid
        self._usr_send_cb: Optional[UsrSendCbT] = None
        self._usr_send_args: Optional[any] = None
        if usr_send_wrapper is not None:
            self._usr_send_cb = usr_send_wrapper[0]
            self._usr_send_args = usr_send_wrapper[1]

        if isinstance(com_if, CommunicationInterface):
            self._com_if = com_if
        else:
            LOGGER.error("CommandSenderReceiver: Invalid communication interface!")
            raise TypeError("CommandSenderReceiver: Invalid communication interface!")

        if isinstance(tm_listener, TmListener):
            self._tm_listener = tm_listener
        else:
            LOGGER.error("CommandSenderReceiver: Invalid TM listener!")
            raise TypeError("Invalid TM Listener!")

        self._start_time = 0
        self._elapsed_time = 0
        self._timeout_counter = 0

        # needed to store last actual TC packet from queue
        self._last_tc = bytearray()
        self._last_tc_obj = None

        # this flag can be used to notify when the operation is finished
        self._operation_pending = False
        # This flag can be used to notify when a reply was received.
        self._reply_received = False

        self._wait_period = 0
        self._wait_start = 0

    def set_tm_timeout(self, tm_timeout: float = -1):
        """
        Set the TM timeout. Usually, the global value set by the args parser is set,
        but the TM timeout can be reset (e.g. for slower architectures)
        :param tm_timeout: New TM timeout value as a float value in seconds
        :return:
        """
        if tm_timeout == -1:
            tm_timeout = get_global(CoreGlobalIds.TM_TIMEOUT)
        self._tm_timeout = tm_timeout

    def set_tc_send_timeout_factor(self, new_factor: float = -1):
        """
        Set the TC resend timeout factor. After self._tm_timeout * new_factor seconds,
        a telecommand will be resent again.
        :param new_factor: Factor as a float number
        :return:
        """
        if new_factor == -1:
            new_factor = get_global(CoreGlobalIds.TC_SEND_TIMEOUT_FACTOR)
        self._tc_send_timeout_factor = new_factor

    def _check_for_first_reply(self) -> None:
        """
        Checks for replies. If no reply is received, send telecommand again in checkForTimeout()
        :return: None
        """
        if self._tm_listener.reply_event():
            self._reply_received = True
            self._operation_pending = False
            self._tm_listener.clear_reply_event()
        else:
            self._check_for_timeout()

    def wait_period_ongoing(
        self,
        sleep_rest_of_wait_period: bool = False,
        set_reply_rcvd_to_true: bool = True,
    ):
        if sleep_rest_of_wait_period:
            # wait rest of wait time
            sleep_time = self._wait_start + self._wait_period - time.time()
            if sleep_time > 0:
                time.sleep(sleep_time)
            LOGGER.info("Wait period over.")
            return False
        # If wait period was specified, we need to wait before checking the next queue entry.
        if self._wait_period > 0:
            if time.time() - self._wait_start < self._wait_period:
                if set_reply_rcvd_to_true:
                    self._reply_received = True
                return True
            else:
                LOGGER.info("Wait period over.")
                self._wait_period = 0
                return False
        else:
            return False

    @staticmethod
    def check_queue_entry_static(tc_queue_entry: TcQueueEntryT) -> bool:
        """Static method to check whether a queue entry is a valid telecommand"""
        queue_entry_first, queue_entry_second = tc_queue_entry
        if isinstance(queue_entry_first, str):
            LOGGER.warning("Invalid telecommand. Queue entry is a string!")
            return False
        if isinstance(queue_entry_first, QueueCommands):
            return False
        elif isinstance(queue_entry_first, bytearray):
            return True
        else:
            return False

    def check_queue_entry(self, tc_queue_entry: TcQueueEntryT) -> bool:
        """
        Checks whether the entry in the pus_tc queue is a telecommand.
        The last telecommand and respective information are stored in _last_tc
        and _last_tc_info
        :param tc_queue_entry:
        :return: True if queue entry is telecommand, False if it is not
        """
        queue_entry_first, queue_entry_second = tc_queue_entry
        queue_entry_is_telecommand = False

        if isinstance(queue_entry_first, str):
            LOGGER.warning("Invalid telecommand. Queue entry is a string!")
            return queue_entry_is_telecommand

        if queue_entry_first == QueueCommands.WAIT:
            wait_time = queue_entry_second
            self._tm_timeout = self._tm_timeout + wait_time
            self._wait_period = wait_time
            LOGGER.info(f"Waiting for {self._wait_period} seconds.")
            self._wait_start = time.time()
        # printout optimized for LOGGER and debugging
        elif queue_entry_first == QueueCommands.PRINT:
            LOGGER.info(queue_entry_second)
        elif queue_entry_first == QueueCommands.RAW_PRINT:
            LOGGER.info(f"Raw command: {queue_entry_second.hex(sep=',')}")
        elif queue_entry_first == QueueCommands.SET_TIMEOUT:
            self._tm_timeout = queue_entry_second
        else:
            self._last_tc, self._last_tc_obj = (queue_entry_first, queue_entry_second)
            return True
        return queue_entry_is_telecommand

    def _check_for_timeout(self, last_timeout: bool = True):
        """
        Checks whether a timeout after sending a telecommand has occured and sends telecommand
        again. If resending reached certain counter, exit the program.
        :return:
        """

        if self._start_time == 0:
            self._start_time = time.time()
        if self._timeout_counter == 5:
            LOGGER.info("CommandSenderReceiver: No response from command !")
            self._operation_pending = False
        if self._start_time != 0:
            self._elapsed_time = time.time() - self._start_time
        if self._elapsed_time >= self._tm_timeout * self._tc_send_timeout_factor:
            from tmtccmd.core.globals_manager import get_global

            if get_global(CoreGlobalIds.RESEND_TC):
                LOGGER.info("CommandSenderReceiver: Timeout, sending TC again !")
                self._com_if.send(self._last_tc)
                self._timeout_counter = self._timeout_counter + 1
                self._start_time = time.time()
            else:
                # todo: we could also stop sending and clear the TC queue
                self._reply_received = True
        time.sleep(0.5)
