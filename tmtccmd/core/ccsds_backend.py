import atexit
import sys
from typing import Optional, Union

from tmtccmd.config.cfg_hook import TmTcCfgHookBase
from tmtccmd.config.definitions import CoreServiceList, CoreModeList
from tmtccmd.core.backend import BackendBase, BackendState, Request, BackendController
from tmtccmd.core.modes import TcMode, TmMode
from tmtccmd.tc.definitions import ProcedureInfo
from tmtccmd.tc.handler import TcHandlerBase, FeedWrapper
from tmtccmd.tc.queue import QueueWrapper
from tmtccmd.logging import get_console_logger
from tmtccmd.tc.ccsds_seq_sender import (
    SequentialCcsdsSender,
    SenderMode,
)
from tmtccmd.tm.ccsds_tm_listener import CcsdsTmListener
from tmtccmd.com_if.com_interface_base import CommunicationInterface

LOGGER = get_console_logger()


class CcsdsTmtcBackend(BackendBase):
    """This is the primary class which handles TMTC reception and sending"""

    def __init__(
        self,
        mode: Union[CoreModeList, int],
        hook_obj: TmTcCfgHookBase,
        com_if: CommunicationInterface,
        tm_listener: CcsdsTmListener,
        tc_handler: TcHandlerBase,
    ):
        self._state = BackendState()
        self._state.mode_wrapper.mode = mode
        if mode == CoreModeList.LISTENER_MODE:
            self._state.mode_wrapper.tm_mode = TmMode.LISTENER
            self._state.mode_wrapper.tc_mode = TcMode.IDLE
        elif mode == CoreModeList.ONE_QUEUE_MODE:
            self._state.mode_wrapper.tm_mode = TmMode.LISTENER
            self._state.mode_wrapper.tc_mode = TcMode.ONE_QUEUE
        elif mode == CoreModeList.MULTI_INTERACTIVE_QUEUE_MODE:
            self._state.mode_wrapper.tc_mode = TcMode.MULTI_QUEUE
            self._state.mode_wrapper.tm_mode = TmMode.LISTENER
        self.__hook_obj = hook_obj
        self.__com_if_active = False
        self.__apid = 0
        self.__tc_handler = tc_handler

        self.__com_if = com_if
        self.__tm_listener = tm_listener
        self._current_proc_info = ProcedureInfo(CoreServiceList.SERVICE_17.value, "0")
        self.exit_on_com_if_init_failure = True
        self._queue_wrapper = QueueWrapper(None)
        self._seq_handler = SequentialCcsdsSender(
            com_if=self.__com_if,
            tc_handler=tc_handler,
            queue_wrapper=self._queue_wrapper,
        )

    @property
    def com_if_id(self):
        return self.__com_if.get_id()

    @property
    def com_if(self) -> CommunicationInterface:
        return self.__com_if

    @property
    def tm_listener(self):
        return self.__tm_listener

    def try_set_com_if(self, com_if: CommunicationInterface):
        if not self.com_if_active():
            self.__com_if = com_if
            self.__tm_listener.com_if(self.__com_if)
        else:
            LOGGER.warning(
                "Communication Interface is active and must be closed first before "
                "reassigning a new one"
            )

    def com_if_active(self):
        return self.__com_if_active

    @property
    def current_proc_info(self) -> ProcedureInfo:
        return self._current_proc_info

    @current_proc_info.setter
    def current_proc_info(self, proc_info: ProcedureInfo):
        self._current_proc_info = proc_info

    @property
    def apid(self) -> int:
        return self.__apid

    @apid.setter
    def apid(self, apid: int):
        self.__apid = apid

    @property
    def mode(self):
        return self._state.mode

    @staticmethod
    def start_handler(executed_handler, ctrl: BackendController):
        if not isinstance(executed_handler, CcsdsTmtcBackend):
            LOGGER.error("Unexpected argument, should be TmTcHandler!")
            sys.exit(1)
        executed_handler.initialize()
        executed_handler.start_listener(ctrl)

    def initialize(self):
        from tmtccmd.utility.exit_handler import keyboard_interrupt_handler

        """
        Perform initialization steps which might be necessary after class construction.
        This has to be called at some point before using the class!
        """
        if self.mode == CoreModeList.LISTENER_MODE:
            LOGGER.info("Running in listener mode..")
        atexit.register(
            keyboard_interrupt_handler, tmtc_backend=self, com_interface=self.__com_if
        )

    def __listener_io_error_handler(self, ctx: str):
        LOGGER.error(f"Communication Interface could not be {ctx}")
        LOGGER.info("TM listener will not be started")
        if self.exit_on_com_if_init_failure:
            LOGGER.error("Closing TMTC commander..")
            self.__com_if.close()
            sys.exit(1)

    def start_listener(self, ctrl: BackendController):
        try:
            self.__com_if.open()
        except IOError:
            self.__listener_io_error_handler("opened")
        self.__com_if_active = True

    def close_listener(self):
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
        try:
            return self.__core_operation()
        except KeyboardInterrupt as e:
            LOGGER.info("Keyboard Interrupt.")
            raise e
        except IOError as e:
            LOGGER.exception("IO Error occured")
            raise e

    def __core_operation(self) -> BackendState:
        self.__handle_action()
        if self.mode == CoreModeList.IDLE:
            self._state.__req = Request.DELAY_IDLE
        elif self.mode == CoreModeList.LISTENER_MODE:
            self._state.__req = Request.DELAY_LISTENER
        return self._state

    def close_com_if(self):
        self.__com_if.close()

    def poll_tm(self):
        """Poll TM, irrespective of current TM mode"""
        self.__tm_listener.operation()

    def __handle_action(self):
        """Command handling."""
        if self._state.tm_mode == TmMode.LISTENER:
            self.__tm_listener.operation()
        elif self._state.tc_mode == TcMode.ONE_QUEUE:
            if not self._seq_handler.mode == SenderMode.DONE:
                service_queue = self.__prepare_tc_queue()
                if service_queue is None:
                    return
                LOGGER.info("Loading TC queue")
                self._seq_handler.queue_wrapper = service_queue
                self._seq_handler.resume()
            self._state._sender_res = self._seq_handler.operation()
            if self._seq_handler.mode == SenderMode.DONE:
                self._state.mode_wrapper.mode = CoreModeList.LISTENER_MODE
                self._state._request = Request.TERMINATION_NO_ERROR
        elif self.mode == CoreModeList.MULTI_INTERACTIVE_QUEUE_MODE:
            # TODO: Handle the queue as long as the current one is full. If it is finished,
            #       request another queue or further instructions from the user, maybe in form
            #       of a special object, using the TC handler feed function
            pass
        else:
            try:
                self.__hook_obj.perform_mode_operation(
                    mode=self.mode, tmtc_backend=self
                )
            except ImportError as error:
                print(error)
                LOGGER.error("Custom mode handling module not provided!")

    def __prepare_tc_queue(self) -> Optional[QueueWrapper]:
        feed_wrapper = FeedWrapper()
        self.__tc_handler.feed_cb(self.current_proc_info, feed_wrapper)
        if not self.__com_if.valid or not feed_wrapper.dispatch_next_queue:
            return None
        return feed_wrapper.current_queue
