"""Used to send multiple TCs in sequence"""
import enum
from typing import Optional

from tmtccmd.tc.definitions import (
    TcQueueEntryBase,
    TcQueueEntryType,
    cast_wait_entry_from_base,
    cast_timeout_entry_from_base,
)
from tmtccmd.tc.handler import TcHandlerBase
from tmtccmd.tc.queue import QueueWrapper
from tmtccmd.com_if.com_interface_base import CommunicationInterface
from tmtccmd.logging import get_console_logger
from tmtccmd.utility.countdown import Countdown

LOGGER = get_console_logger()


class SenderMode(enum.IntEnum):
    IDLE = 0
    BUSY = 1
    DONE = 2


class SeqResultWrapper:
    def __init__(self, mode: SenderMode):
        self.mode = mode


class SequentialCcsdsSender:
    """Specific implementation of CommandSenderReceiver to send multiple telecommands in sequence"""

    def __init__(
        self,
        queue_wrapper: QueueWrapper,
        com_if: CommunicationInterface,
        tc_handler: TcHandlerBase,
    ):
        """
        :param queue_wrapper: Wrapper object containing the queue and queue handling properties
        :param tc_handler:
        :param com_if:          CommunicationInterface object, passed on to CommandSenderReceiver
        """
        self._com_if = com_if
        self._tc_handler = tc_handler
        self._queue_wrapper = queue_wrapper
        # This flag can be used to notify the sender to send the next TC
        self._next_send_condition = True
        self._mode = SenderMode.IDLE
        self._wait_cd = Countdown(0)
        self._send_cd = Countdown(queue_wrapper.inter_cmd_delay)
        self._current_res = SeqResultWrapper(self._mode)
        self._op_divider = 0
        self._last_queue_entry: Optional[TcQueueEntryBase] = None
        self._last_tc: Optional[TcQueueEntryBase] = None

    @property
    def queue_wrapper(self):
        return self._queue_wrapper

    @queue_wrapper.setter
    def queue_wrapper(self, queue_wrapper: QueueWrapper):
        if self._mode == SenderMode.BUSY:
            raise ValueError("Busy with other queue")
        self._mode = SenderMode.BUSY
        # Set to true for first packet, otherwise nothing will be sent.
        self._next_send_condition = True
        self._queue_wrapper = queue_wrapper

    def handle_new_queue_forced(self, queue_wrapper: QueueWrapper):
        self._mode = SenderMode.IDLE
        self.queue_wrapper = queue_wrapper

    def pause(self):
        self._mode = SenderMode.IDLE

    def operation(self) -> SeqResultWrapper:
        if not self.queue_wrapper.queue and self._mode != SenderMode.DONE:
            self._mode = SenderMode.DONE
        if self._mode == SenderMode.IDLE or self._mode == SenderMode.DONE:
            return SeqResultWrapper(self._mode)
        self._handle_current_tc_queue()

    def _handle_current_tc_queue(self):
        """Primary function which is called for sequential transfer.
        :return:
        """
        # Do not use continue anywhere in this while loop for now
        if not self.queue_wrapper.queue:
            if self._wait_cd.timed_out() and self._send_cd.timed_out():
                # cache this for last wait time
                self._mode = SenderMode.DONE
        else:
            if not self._send_cd.busy() and not self._wait_cd.busy():
                self._send_next_telecommand()
        self.__print_rem_timeout(op_divider=self._op_divider)
        self._op_divider += 1

    def __print_rem_timeout(self, op_divider: int, divisor: int = 15):
        if self._wait_cd.busy() and op_divider % divisor == 0:
            rem_time = self._wait_cd.rem_time()
            if self._wait_cd.rem_time() > 0:
                LOGGER.info(f"{rem_time:.01f} seconds wait time remaining")

    def _send_next_telecommand(self):
        """Sends the next telecommand and returns whether an actual telecommand was sent"""
        next_queue_entry = self.queue_wrapper.queue.pop()
        if self.check_queue_entry(next_queue_entry):
            self._send_cd.reset()
        self._tc_handler.send_cb(next_queue_entry, self._com_if)

    def check_queue_entry(self, queue_entry: TcQueueEntryBase) -> bool:
        """
        Checks whether the entry in the pus_tc queue is a telecommand.
        :param queue_entry: Generic queue entry
        :return: True if queue entry is telecommand, False if it is not
        """
        if not isinstance(queue_entry, TcQueueEntryBase):
            LOGGER.warning("Invalid queue entry detected")
            raise ValueError("Invalid queue entry detected")

        if queue_entry.etype == TcQueueEntryType.WAIT:
            wait_entry = cast_wait_entry_from_base(queue_entry)
            LOGGER.info(f"Waiting for {wait_entry.wait_time} seconds.")
            self._wait_cd.reset(new_timeout=wait_entry.wait_time)
        elif queue_entry.etype == TcQueueEntryType.SET_INTER_CMD_DELAY:
            timeout_entry = cast_timeout_entry_from_base(queue_entry)
            self._send_cd.reset(new_timeout=timeout_entry.timeout_secs)
        is_tc = False
        if (
            queue_entry.etype == TcQueueEntryType.RAW_TC
            or queue_entry.etype == TcQueueEntryType.PUS_TC
        ):
            self._last_tc = queue_entry
            is_tc = True
        self._last_queue_entry = queue_entry
        return is_tc
