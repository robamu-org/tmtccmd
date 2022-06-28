import atexit
import sys
import threading
from collections import deque
from datetime import timedelta
from typing import Optional

from tmtccmd.core import (
    BackendBase,
    BackendState,
    BackendRequest,
    BackendController,
    TcMode,
    TmMode,
)
from tmtccmd.tc import TcProcedureBase
from tmtccmd.tc.handler import TcHandlerBase, FeedWrapper
from tmtccmd.utility.exit_handler import keyboard_interrupt_handler
from tmtccmd.tc.queue import QueueWrapper
from tmtccmd.logging import get_console_logger
from tmtccmd.tc.ccsds_seq_sender import (
    SequentialCcsdsSender,
    SenderMode,
)
from tmtccmd.tm.ccsds_tm_listener import CcsdsTmListener
from tmtccmd.com_if import ComInterface

LOGGER = get_console_logger()


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

        self.__com_if_active = False
        self.__tc_handler = tc_handler

        self.__com_if = com_if
        self.__tm_listener = tm_listener
        self._current_procedure: Optional[TcProcedureBase] = None
        self.exit_on_com_if_init_failure = True
        self._queue_wrapper = QueueWrapper(None, deque())
        self._seq_handler = SequentialCcsdsSender(
            com_if=self.__com_if,
            tc_handler=tc_handler,
            queue_wrapper=self._queue_wrapper,
        )
        self._backend_lock: Optional[threading.Lock] = None

    def register_keyboard_interrupt_handler(self):
        """Register a keyboard interrupt handler which closes the COM interface and prints
        a small message"""
        atexit.register(keyboard_interrupt_handler, self)

    @property
    def com_if_id(self):
        return self.__com_if.get_id()

    @property
    def com_if(self) -> ComInterface:
        return self.__com_if

    @property
    def state(self):
        return self._state

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
        self._state.mode_wrapper._tc_mode = tc_mode

    @tm_mode.setter
    def tm_mode(self, tm_mode: TmMode):
        self._state.mode_wrapper._tm_mode = tm_mode

    @property
    def tm_listener(self):
        return self.__tm_listener

    def try_set_com_if(self, com_if: ComInterface) -> bool:
        if not self.com_if_active():
            self.__com_if = com_if
            return True
        else:
            return False

    def com_if_active(self):
        return self.__com_if_active

    @property
    def current_proc_info(self) -> TcProcedureBase:
        return self._current_procedure

    @current_proc_info.setter
    def current_proc_info(self, proc_info: TcProcedureBase):
        self._current_procedure = proc_info

    def start(self):
        self.open_com_if()

    def __listener_io_error_handler(self, ctx: str):
        LOGGER.error(f"Communication Interface could not be {ctx}")
        LOGGER.info("TM listener will not be started")
        if self.exit_on_com_if_init_failure:
            LOGGER.error("Closing TMTC commander..")
            self.__com_if.close()
            sys.exit(1)

    def open_com_if(self):
        try:
            self.__com_if.open()
        except IOError:
            self.__listener_io_error_handler("opened")
        self.__com_if_active = True

    def close_com_if(self):
        """Closes the TM listener and the communication interface. This is started in a separarate
        thread because the communication interface might still be busy. The completion can be
        checked with :meth:`tmtccmd.core.backend.is_com_if_active`. Alternatively, waiting on
        completion is possible by specifying the join argument and a timeout in
        floating point second.
        :return:
        """
        try:
            self.__com_if.close()
        except IOError:
            self.__listener_io_error_handler("close")
        self.__com_if_active = False

    def periodic_op(self, ctrl: BackendController) -> BackendState:
        """Periodic operation
        :raises KeyboardInterrupt: Yields info output and then propagates the exception
        :raises IOError: Yields informative output and propagates exception
        :"""
        self.default_operation()
        return self._state

    def default_operation(self):
        """Command handling."""
        self.tm_operation()
        self.tc_operation()
        self.mode_to_req()

    def mode_to_req(self):
        if self.tc_mode == TcMode.IDLE and self.tm_mode == TmMode.IDLE:
            self._state._req = BackendRequest.DELAY_IDLE
        elif self.tm_mode == TmMode.LISTENER and self.tc_mode == TcMode.IDLE:
            self._state._req = BackendRequest.DELAY_LISTENER
        elif self._seq_handler.mode == SenderMode.DONE:
            if self._state.tc_mode == TcMode.ONE_QUEUE:
                self.tc_mode = TcMode.IDLE
                self._state._req = BackendRequest.TERMINATION_NO_ERROR
            elif self._state.tc_mode == TcMode.MULTI_QUEUE:
                self._state.mode_wrapper.tc_mode = TcMode.IDLE
                self._state._req = BackendRequest.CALL_NEXT
        else:
            if self._state.sender_res.longest_rem_delay.total_seconds() * 1000 > 0:
                self._state._recommended_delay = (
                    self._state.sender_res.longest_rem_delay
                )
                self._state._req = BackendRequest.DELAY_CUSTOM
            else:
                self._state._req = BackendRequest.CALL_NEXT

    def poll_tm(self):
        """Poll TM, irrespective of current TM mode"""
        self.__tm_listener.operation(self.__com_if)

    def tm_operation(self):
        if self._state.tm_mode == TmMode.LISTENER:
            self.__tm_listener.operation(self.__com_if)

    def tc_operation(self):
        if self._state.tc_mode != TcMode.IDLE:
            self.__check_and_execute_queue()

    def __check_and_execute_queue(self):
        if self._seq_handler.mode == SenderMode.DONE:
            queue = self.__prepare_tc_queue()
            if queue is None:
                return
            LOGGER.info("Loading TC queue")
            self._seq_handler.queue_wrapper = queue
            self._seq_handler.resume()
        self._state._sender_res = self._seq_handler.operation()

    def __prepare_tc_queue(self, auto_dispatch: bool = True) -> Optional[QueueWrapper]:
        feed_wrapper = FeedWrapper(self._queue_wrapper, auto_dispatch)
        self.__tc_handler.feed_cb(self.current_proc_info, feed_wrapper)
        self._queue_wrapper.info = self.current_proc_info
        if not self.__com_if.valid or not feed_wrapper.dispatch_next_queue:
            return None
        return feed_wrapper.queue_helper.queue_wrapper
