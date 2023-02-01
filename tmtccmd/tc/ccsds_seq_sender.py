"""Used to send multiple TCs in sequence"""
import enum
import logging
from datetime import timedelta
from typing import Optional

from tmtccmd.tc import (
    TcQueueEntryBase,
    TcQueueEntryType,
    QueueEntryHelper,
    ProcedureWrapper,
)
from tmtccmd.tc.handler import TcHandlerBase, SendCbParams
from tmtccmd.tc.queue import QueueWrapper
from tmtccmd.com import ComInterface
from tmtccmd.util.countdown import Countdown


class SenderMode(enum.IntEnum):
    BUSY = 0
    DONE = 1


class SeqResultWrapper:
    def __init__(self, mode: SenderMode):
        self.mode = mode
        self.longest_rem_delay: timedelta = timedelta()
        self.tc_sent: bool = False
        self.queue_empty: bool = False
        self.next_entry_is_tc: bool = False


class SequentialCcsdsSender:
    """Specific implementation of CommandSenderReceiver to send multiple telecommands in sequence"""

    def __init__(
        self,
        queue_wrapper: QueueWrapper,
        tc_handler: TcHandlerBase,
    ):
        """
        :param queue_wrapper: Wrapper object containing the queue and queue handling properties
        :param tc_handler:
        """
        self._tc_handler = tc_handler
        self._queue_wrapper = queue_wrapper
        self._proc_wrapper = ProcedureWrapper(None)
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
        self._current_res.longest_rem_delay = queue_wrapper.inter_cmd_delay
        self._proc_wrapper.base = self._queue_wrapper.info
        self._queue_wrapper = queue_wrapper

    def handle_new_queue_forced(self, queue_wrapper: QueueWrapper):
        self._mode = SenderMode.DONE
        self.queue_wrapper = queue_wrapper
        self._proc_wrapper.base = self._queue_wrapper.info

    def resume(self):
        """Can be used to resume a finished sequential sender it the provided queue is
        not empty anymore"""
        if self._mode == SenderMode.DONE and self.queue_wrapper.queue:
            self._mode = SenderMode.BUSY

    def operation(self, com_if: ComInterface) -> SeqResultWrapper:
        """Primary function which should be called periodically to consume a TC queue.

        :param com_if: Communication interface used to send telecommands. Will be passed to the
            user send function
        """
        self._handle_current_tc_queue(com_if)
        self._current_res.mode = self._mode
        return self._current_res

    @property
    def mode(self):
        return self._mode

    def _handle_current_tc_queue(self, com_if: ComInterface):
        """Primary function which is called for sequential transfer.
        :return:
        """
        # Do not use continue anywhere in this while loop for now
        if not self.queue_wrapper.queue:
            self._current_res.queue_empty = True
            if self.no_delay_remaining():
                self._proc_wrapper.base = self._queue_wrapper.info
                # cache this for last wait time
                self._tc_handler.queue_finished_cb(self._proc_wrapper)
                self._mode = SenderMode.DONE
                return
        else:
            self._current_res.queue_empty = False
            self._check_next_telecommand(com_if)
        self._update_largest_delay()
        self.__print_rem_timeout(op_divider=self._op_divider)
        self._op_divider += 1

    def __print_rem_timeout(self, op_divider: int, divisor: int = 15):
        if not self.__wait_cd_timed_out() and op_divider % divisor == 0:
            rem_time = self._wait_cd.rem_time()
            if self._wait_cd.rem_time() > timedelta():
                print(f"{rem_time.total_seconds():.01f} seconds wait time remaining")

    def _check_next_telecommand(self, com_if: ComInterface):
        """Sends the next telecommand and returns whether an actual telecommand was sent"""
        next_queue_entry = self.queue_wrapper.queue[0]
        is_tc = self.handle_non_tc_entry(next_queue_entry)
        consume_queue_entry = True
        if is_tc:
            if self.no_delay_remaining():
                self._current_res.tc_sent = True
            else:
                self._current_res.tc_sent = False
                consume_queue_entry = False
        else:
            self._current_res.tc_sent = False
        if consume_queue_entry:
            self._tc_handler.send_cb(
                SendCbParams(
                    self._proc_wrapper, QueueEntryHelper(next_queue_entry), com_if
                )
            )
            if is_tc:
                if self.queue_wrapper.inter_cmd_delay != self._send_cd.timeout:
                    self._send_cd.reset(self.queue_wrapper.inter_cmd_delay)
                else:
                    self._send_cd.reset()
            self.queue_wrapper.queue.popleft()
            if self.queue_wrapper.queue:
                self._current_res.next_entry_is_tc = self.queue_wrapper.queue[0].is_tc()
            else:
                self._current_res.next_entry_is_tc = False
        if not self.queue_wrapper.queue and self.no_delay_remaining():
            self._tc_handler.queue_finished_cb(
                ProcedureWrapper(self._queue_wrapper.info)
            )
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
            raise ValueError("Invalid queue entry detected")
        cast_wrapper = QueueEntryHelper(queue_entry)
        if queue_entry.etype == TcQueueEntryType.WAIT:
            wait_entry = cast_wrapper.to_wait_entry()
            logging.getLogger(__name__).info(
                f"Waiting for {wait_entry.wait_time.total_seconds() * 1000} milliseconds."
            )
            self._wait_cd.reset(new_timeout=wait_entry.wait_time)
        elif queue_entry.etype == TcQueueEntryType.PACKET_DELAY:
            timeout_entry = cast_wrapper.to_packet_delay_entry()
            self.queue_wrapper.inter_cmd_delay = timeout_entry.delay_time
            self._send_cd.reset(new_timeout=timeout_entry.delay_time)
        is_tc = queue_entry.is_tc()
        if is_tc:
            self._last_tc = queue_entry
        self._last_queue_entry = queue_entry
        return is_tc

    def _update_largest_delay(self):
        self._current_res.longest_rem_delay = max(
            self._wait_cd.rem_time(), self._send_cd.rem_time()
        )
