"""Used to send multiple TCs in sequence"""
import enum
import math
from datetime import timedelta
from typing import Optional

from tmtccmd.tc import TcQueueEntryBase, TcQueueEntryType, PacketCastWrapper
from tmtccmd.tc.handler import TcHandlerBase
from tmtccmd.tc.queue import QueueWrapper
from tmtccmd.com_if import ComInterface
from tmtccmd.logging import get_console_logger
from tmtccmd.utility.countdown import Countdown

LOGGER = get_console_logger()


class SenderMode(enum.IntEnum):
    BUSY = 0
    DONE = 1


class SeqResultWrapper:
    def __init__(self, mode: SenderMode):
        self.mode = mode
        self.longest_rem_delay: timedelta = timedelta()
        self.tc_sent: bool = False


class SequentialCcsdsSender:
    """Specific implementation of CommandSenderReceiver to send multiple telecommands in sequence"""

    def __init__(
        self,
        queue_wrapper: QueueWrapper,
        com_if: ComInterface,
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
        self._mode = SenderMode.DONE
        self._wait_cd = Countdown(None)
        self._send_cd = Countdown(queue_wrapper.inter_cmd_delay)
        self._current_res = SeqResultWrapper(self._mode)
        self._current_res.longest_rem_delay = queue_wrapper.inter_cmd_delay
        self._op_divider = 0
        self._last_queue_entry: Optional[TcQueueEntryBase] = None
        self._last_tc: Optional[TcQueueEntryBase] = None

    @property
    def queue_wrapper(self):
        return self._queue_wrapper

    @queue_wrapper.setter
    def queue_wrapper(self, queue_wrapper: QueueWrapper):
        """This setter throws a ValueError if the sequential sender is busy with another queue"""
        if self._mode == SenderMode.BUSY:
            raise ValueError("Busy with other queue")
        self._mode = SenderMode.BUSY
        # There is no need to delay sending of the first entry, the send delay is inter-packet
        # only
        self._send_cd.timeout = timedelta()
        self._queue_wrapper = queue_wrapper

    def handle_new_queue_forced(self, queue_wrapper: QueueWrapper):
        self._mode = SenderMode.DONE
        self.queue_wrapper = queue_wrapper

    def resume(self):
        """Can be used to resume a finished sequential sender it the provided queue is
        not empty anymore"""
        if self._mode == SenderMode.DONE and self.queue_wrapper.queue:
            self._mode = SenderMode.BUSY

    def operation(self) -> SeqResultWrapper:
        self._handle_current_tc_queue()
        self._current_res.mode = self._mode
        return self._current_res

    @property
    def mode(self):
        return self._mode

    def _handle_current_tc_queue(self):
        """Primary function which is called for sequential transfer.
        :return:
        """
        # Do not use continue anywhere in this while loop for now
        if not self.queue_wrapper.queue:
            if self.no_delay_remaining():
                # cache this for last wait time
                self._tc_handler.queue_finished_cb(self._queue_wrapper.info)
                self._mode = SenderMode.DONE
                return
        else:
            self._check_next_telecommand()
        self.__print_rem_timeout(op_divider=self._op_divider)
        self._op_divider += 1

    def __print_rem_timeout(self, op_divider: int, divisor: int = 15):
        if not self.__wait_cd_timed_out() and op_divider % divisor == 0:
            rem_time = self._wait_cd.rem_time()
            if self._wait_cd.rem_time() > timedelta():
                LOGGER.info(
                    f"{rem_time.total_seconds():.01f} seconds wait time remaining"
                )

    def _check_next_telecommand(self):
        """Sends the next telecommand and returns whether an actual telecommand was sent"""
        next_queue_entry = self.queue_wrapper.queue[0]
        is_tc = self.handle_non_tc_entry(next_queue_entry)
        call_send_cb = True
        if is_tc:
            if self.no_delay_remaining():
                self._current_res.tc_sent = True
            else:
                self._current_res.tc_sent = False
                call_send_cb = False
        else:
            self._current_res.tc_sent = False
        if call_send_cb:
            self._tc_handler.send_cb(next_queue_entry, self._com_if)
            if is_tc:
                if self.queue_wrapper.inter_cmd_delay != self._send_cd.timeout:
                    self._send_cd.reset(self.queue_wrapper.inter_cmd_delay)
                else:
                    self._send_cd.reset()
            self.queue_wrapper.queue.popleft()
        if not self.queue_wrapper.queue and self.no_delay_remaining():
            self._tc_handler.queue_finished_cb(self._queue_wrapper.info)
            self._mode = SenderMode.DONE

    def no_delay_remaining(self) -> bool:
        return self.__send_cd_timed_out() and self.__wait_cd_timed_out()

    def __send_cd_timed_out(self):
        """Internal wrapper API to allow easier testing"""
        return self._send_cd.timed_out()

    def __wait_cd_timed_out(self):
        """Internal wrapper API to allow easier testing"""
        return self._wait_cd.timed_out()

    def handle_non_tc_entry(self, queue_entry: TcQueueEntryBase) -> bool:
        """
        Checks whether the entry in the pus_tc queue is a telecommand.
        :param queue_entry: Generic queue entry
        :return: True if queue entry is telecommand, False if it is not
        """
        if not isinstance(queue_entry, TcQueueEntryBase):
            LOGGER.warning("Invalid queue entry detected")
            raise ValueError("Invalid queue entry detected")
        cast_wrapper = PacketCastWrapper(queue_entry)
        if queue_entry.etype == TcQueueEntryType.WAIT:
            wait_entry = cast_wrapper.to_wait_entry()
            LOGGER.info(
                f"Waiting for {wait_entry.wait_time.total_seconds() * 1000} milliseconds."
            )
            self._wait_cd.reset(new_timeout=wait_entry.wait_time)
            self._current_res.longest_rem_delay = max(
                self._wait_cd.rem_time(), self._send_cd.rem_time()
            )
        elif queue_entry.etype == TcQueueEntryType.PACKET_DELAY:
            timeout_entry = cast_wrapper.to_packet_delay_entry()
            self.queue_wrapper.inter_cmd_delay = timeout_entry.delay_time
            self._send_cd.reset(new_timeout=timeout_entry.delay_time)
            self._current_res.longest_rem_delay = max(
                self._wait_cd.rem_time(), self._send_cd.rem_time()
            )
        is_tc = queue_entry.is_tc()
        if is_tc:
            self._last_tc = queue_entry
        self._last_queue_entry = queue_entry
        return is_tc
