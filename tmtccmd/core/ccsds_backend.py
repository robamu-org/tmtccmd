import atexit
import logging
import sys
from collections import deque
from datetime import timedelta
from typing import Optional

from tmtccmd.core.backend_base import BackendBase
from tmtccmd.core.backend_state import BackendState
from tmtccmd.core.base import TcMode, TmMode, BackendRequest
from tmtccmd.tc import TcProcedureBase, ProcedureWrapper
from tmtccmd.tc.handler import TcHandlerBase, FeedWrapper
from tmtccmd.util.exit import keyboard_interrupt_handler
from tmtccmd.tc.queue import QueueWrapper
from tmtccmd.tc.ccsds_seq_sender import (
    SequentialCcsdsSender,
    SenderMode,
)
from tmtccmd.tm.ccsds_tm_listener import CcsdsTmListener
from tmtccmd.com import ComInterface


class NoValidProcedureSet(Exception):
    pass


class CcsdsTmtcBackend(BackendBase):
    """This is the primary class which handles TMTC reception and sending"""

    def __init__(
        self,
        tc_mode: TcMode,
        tm_mode: TmMode,
        com_if: ComInterface,
        tm_listener: CcsdsTmListener,
        tc_handler: TcHandlerBase,
    ):
        self._state = BackendState()
        self._state.mode_wrapper.tc_mode = tc_mode
        self._state.mode_wrapper.tm_mode = tm_mode

        self._com_if_active = False
        self._tc_handler = tc_handler

        self._com_if = com_if
        self._tm_listener = tm_listener
        self.exit_on_com_if_init_failure = True
        # This can be used to keep the TC mode in multi queue mode after finishing the handling
        # of a queue
        self.keep_multi_queue_mode = False
        self.keep_listener_mode = False
        self._queue_wrapper = QueueWrapper(None, deque())
        self._seq_handler = SequentialCcsdsSender(
            tc_handler=tc_handler,
            queue_wrapper=self._queue_wrapper,
        )

    def register_keyboard_interrupt_handler(self):
        """Register a keyboard interrupt handler which closes the COM interface and prints
        a small message"""
        atexit.register(keyboard_interrupt_handler, self)

    @property
    def com_if_id(self):
        return self._com_if.id

    @property
    def com_if(self) -> ComInterface:
        return self._com_if

    @property
    def state(self):
        return self._state

    @property
    def request(self):
        return self._state.request

    @property
    def tc_mode(self):
        return self._state.mode_wrapper.tc_mode

    @property
    def tm_mode(self):
        return self._state.mode_wrapper.tm_mode

    @property
    def inter_cmd_delay(self):
        return self._queue_wrapper.inter_cmd_delay

    @inter_cmd_delay.setter
    def inter_cmd_delay(self, delay: timedelta):
        self._queue_wrapper.inter_cmd_delay = delay

    @tc_mode.setter
    def tc_mode(self, tc_mode: TcMode):
        self._state.mode_wrapper.tc_mode = tc_mode

    @tm_mode.setter
    def tm_mode(self, tm_mode: TmMode):
        self._state.mode_wrapper.tm_mode = tm_mode

    @property
    def tm_listener(self):
        return self._tm_listener

    def try_set_com_if(self, com_if: ComInterface) -> bool:
        if not self.com_if_active():
            self._com_if = com_if
            return True
        else:
            return False

    def com_if_active(self):
        return self._com_if_active

    @property
    def current_procedure(self) -> ProcedureWrapper:
        return ProcedureWrapper(self._queue_wrapper.info)

    @current_procedure.setter
    def current_procedure(self, proc_info: TcProcedureBase):
        self._queue_wrapper.info = proc_info

    def start(self):
        self.open_com_if()

    def __listener_io_error_handler(self, ctx: str):
        logger = logging.getLogger(__name__)
        logger.error(f"Communication Interface could not be {ctx}")
        logger.info("TM listener will not be started")
        if self.exit_on_com_if_init_failure:
            logger.error("Closing TMTC commander..")
            self._com_if.close()
            sys.exit(1)

    def open_com_if(self):
        try:
            self._com_if.open()
        except IOError:
            self.__listener_io_error_handler("opened")
        self._com_if_active = True

    def close_com_if(self):
        """Closes the TM listener and the communication interface
        :return:
        """
        try:
            self._com_if.close()
        except IOError:
            self.__listener_io_error_handler("close")
        self._com_if_active = False

    def periodic_op(self, _args: Optional[any] = None) -> BackendState:
        """Periodic operation. Simply calls the :py:meth:`default_operation` function.
        :raises KeyboardInterrupt: Yields info output and then propagates the exception
        :raises IOError: Yields informative output and propagates exception
        :"""
        self.default_operation()
        return self._state

    def default_operation(self):
        """Command handling. This is a convenience function to call the TM and the TC operation
        and then auto-determine the internal mode with the :py:meth:`mode_to_req` method.

        :raises NoValidProcedureSet: No valid procedure set to be passed to the feed callback of
            the TC handler
        """
        self.tm_operation()
        self.tc_operation()
        self.mode_to_req()

    def mode_to_req(self):
        """This function will convert the internal state of the backend to a backend
        :py:attr:`request`,  which can be used to determine the next operation. These requests can
        be treated like recommendations.
        For example, for if both the TC and the TM mode are IDLE, the request will be set to
        :py:attr:`BackendRequest.DELAY_IDLE` field.
        """
        if self.tc_mode == TcMode.IDLE and self.tm_mode == TmMode.IDLE:
            self._state._req = BackendRequest.DELAY_IDLE
        elif self.tm_mode == TmMode.LISTENER and self.tc_mode == TcMode.IDLE:
            self._state._req = BackendRequest.DELAY_LISTENER
        elif self._seq_handler.mode == SenderMode.DONE:
            if self._state.tc_mode == TcMode.ONE_QUEUE:
                if self.keep_listener_mode:
                    self._state._req = BackendRequest.DELAY_LISTENER
                    self.tm_mode = TmMode.LISTENER
                    self.tc_mode = TcMode.IDLE
                else:
                    self.tc_mode = TcMode.IDLE
                    self._state._req = BackendRequest.TERMINATION_NO_ERROR
            elif self._state.tc_mode == TcMode.MULTI_QUEUE:
                if not self.keep_multi_queue_mode:
                    self._state.mode_wrapper.tc_mode = TcMode.IDLE
                self._state._req = BackendRequest.CALL_NEXT
        else:
            if (
                not self._state.sender_res.next_entry_is_tc
                and not self._state.sender_res.queue_empty
            ):
                self._state._req = BackendRequest.CALL_NEXT
            else:
                if (
                    int(self._state.sender_res.longest_rem_delay.microseconds / 1000.0)
                    > 0
                ):
                    self._state._recommended_delay = (
                        self._state.sender_res.longest_rem_delay
                    )
                    self._state._req = BackendRequest.DELAY_CUSTOM
                else:
                    self._state._req = BackendRequest.CALL_NEXT

    def poll_tm(self):
        """Poll TM, irrespective of current TM mode"""
        self._tm_listener.operation(self._com_if)

    def tm_operation(self):
        """This function will fetch and forward TM data from the current communication interface
        to the user TM handler. It only does so if the :py:attr:`tm_mode` is set to the LISTENER
        mode
        """
        if self._state.tm_mode == TmMode.LISTENER:
            self._tm_listener.operation(self._com_if)

    def tc_operation(self):
        """This function will handle consuming the current TC queue
        if one is available, or attempting to fetch a new one if it is not. This function will only
        do something if the :py:attr:`tc_mode` is set to a non IDLE value.

        It is necessary to set a valid procedure before calling this by using the
        :py:attr:`current_proc_info` setter function.

        :raises NoValidProcedureSet: No valid procedure set to be passed to the feed callback of
            the TC handler
        """
        if self._state.tc_mode != TcMode.IDLE:
            self.__check_and_execute_queue()

    def __check_and_execute_queue(self):
        if self._seq_handler.mode == SenderMode.DONE:
            queue = self.__prepare_tc_queue()
            if queue is None:
                return
            logging.getLogger(__name__).info("Loading TC queue")
            self._seq_handler.queue_wrapper = queue
            self._seq_handler.resume()
        self._state._sender_res = self._seq_handler.operation(self._com_if)

    def __prepare_tc_queue(self, auto_dispatch: bool = True) -> Optional[QueueWrapper]:
        feed_wrapper = FeedWrapper(self._queue_wrapper, auto_dispatch)
        if self._queue_wrapper.info is None:
            raise NoValidProcedureSet(
                "No procedure was set to pass to the feed callback function"
            )
        self._tc_handler.feed_cb(
            ProcedureWrapper(self._queue_wrapper.info), feed_wrapper
        )
        if not feed_wrapper.dispatch_next_queue:
            return None
        return feed_wrapper.queue_wrapper
