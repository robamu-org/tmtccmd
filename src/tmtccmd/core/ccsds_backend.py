import atexit
import time
import sys
from threading import Thread
from typing import cast, Optional

from tmtccmd.config.cfg_hook import TmTcCfgHookBase
from tmtccmd.config.definitions import CoreServiceList, CoreModeList
from tmtccmd.core.backend import BackendBase, BackendState, Request, BackendController
from tmtccmd.tc.definitions import ProcedureInfo
from tmtccmd.tc.handler import TcHandlerBase
from tmtccmd.tc.queue import QueueWrapper
from tmtccmd.tm.definitions import TmTypes
from tmtccmd.tm.handler import TmHandlerBase
from tmtccmd.logging import get_console_logger
from tmtccmd.tc.ccsds_seq_sender_receiver import (
    SequentialCcsdsSenderReceiver,
)
from tmtccmd.tm.ccsds_tm_listener import CcsdsTmListener
from tmtccmd.ccsds.handler import CcsdsTmHandler
from tmtccmd.com_if.com_interface_base import CommunicationInterface


LOGGER = get_console_logger()


class CcsdsTmtcBackend(BackendBase):
    """This is the primary class which handles TMTC reception and sending"""

    def __init__(
        self,
        hook_obj: TmTcCfgHookBase,
        com_if: CommunicationInterface,
        tm_listener: CcsdsTmListener,
        tm_handler: TmHandlerBase,
        tc_handler: TcHandlerBase,
    ):
        self.mode = CoreModeList.LISTENER_MODE
        self.com_if_key = com_if.get_id()
        self.__hook_obj = hook_obj
        self.__com_if_active = False
        self.__apid = 0
        self.__res = BackendState(Request.NONE)
        self.__tc_handler = tc_handler

        # This flag could be used later to command the TMTC Client with a front-end
        self.one_shot_operation = False

        self.__com_if = com_if
        self.__tm_listener = tm_listener
        self._current_proc_info = ProcedureInfo(CoreServiceList.SERVICE_17.value, "0")
        if tm_handler.get_type() == TmTypes.CCSDS_SPACE_PACKETS:
            self.__tm_handler: CcsdsTmHandler = cast(CcsdsTmHandler, tm_handler)
            for apid_queue_len_tuple in self.__tm_handler.get_apid_queue_len_list():
                self.__tm_listener.subscribe_ccsds_tm_handler(
                    apid_queue_len_tuple[0], apid_queue_len_tuple[1]
                )
        self.exit_on_com_if_init_failure = True
        self._queue_wrapper = QueueWrapper(None)
        self._seq_handler = SequentialCcsdsSenderReceiver(
            com_if=self.__com_if,
            tm_handler=self.__tm_handler,
            tm_listener=self.__tm_listener,
            tc_handler=tc_handler,
            apid=self.__apid,
            queue_wrapper=self._queue_wrapper,
        )

    @property
    def com_if_id(self):
        return self.com_if_key

    @property
    def com_if(self) -> CommunicationInterface:
        return self.__com_if

    @property
    def tm_listener(self):
        return self.__tm_listener

    def set_com_if(self, com_if: CommunicationInterface):
        if not self.is_com_if_active():
            self.__com_if = com_if
            self.__tm_listener.set_com_if(self.__com_if)
        else:
            LOGGER.warning(
                "Communication Interface is active and must be closed first before "
                "reassigning a new one"
            )

    def is_com_if_active(self):
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
        try:
            self.__tm_listener.start()
        except IOError:
            self.__listener_io_error_handler("started")
        self.__com_if_active = True
        self.periodic_op(ctrl)

    def close_listener(self, join: bool = False, join_timeout_seconds: float = 1.0):
        """Closes the TM listener and the communication interface. This is started in a separarate
        thread because the communication interface might still be busy. The completion can be
        checked with :meth:`tmtccmd.core.backend.is_com_if_active`. Alternatively, waiting on
        completion is possible by specifying the join argument and a timeout in
        floating point second.
        :param join:
        :param join_timeout_seconds:
        :return:
        """
        if self.__com_if_active:
            close_thread = Thread(target=self.__com_if_closing)
            close_thread.start()
            if join:
                close_thread.join(timeout=join_timeout_seconds)

    def periodic_op(self, ctrl: BackendController) -> BackendState:
        """Periodic operation
        :raises KeyboardInterrupt: Yields info output and then propagates the exception
        :raises IOError: Yields informative output and propagates exception
        :"""
        try:
            return self.__core_operation(self.one_shot_operation)
        except KeyboardInterrupt as e:
            LOGGER.info("Keyboard Interrupt.")
            raise e
        except IOError as e:
            LOGGER.exception("IO Error occured")
            raise e

    def __core_operation(self, one_shot: bool) -> BackendState:
        self.__handle_action()
        if one_shot:
            self.__res.req = Request.TERMINATION_NO_ERROR
        else:
            if self.mode == CoreModeList.IDLE:
                self.__res.req = Request.DELAY_IDLE
            elif self.mode == CoreModeList.LISTENER_MODE:
                self.__res.req = Request.DELAY_LISTENER
        return self.__res

    def __com_if_closing(self):
        self.__tm_listener.stop()
        while True:
            if not self.__tm_listener.is_listener_active():
                self.__com_if.close()
                self.__com_if_active = False
                break
            else:
                time.sleep(0.2)

    def __handle_action(self):
        """Command handling."""
        # TODO: It should be possible to call this function discretely. This avoids having to
        #       start receiver threads in the backgrounds. The backend should then perform the
        #       periodic TM polling here, with a configurable polling frequency.
        #       In total this needs to be done like this: In One Queue Mode, request a queue
        #       from the user if there is not one available yet. If one is available, consume it
        #       on every operation call. If the queue was consumed, request program termination
        #       or mode change. This is done using the one-shot flag, so the ONE SHOT MODE is tied
        #       to that flag.
        #       For multi-mode do the same, but instead of requesting program termination, use
        #       the feed function of the TC handler to request another queue
        # TODO: This this that is done for the listener mode: Do it for all modes with a
        #       configurable polling delay. TM should be polled and handled independently of TC,
        #       or tying them together in some way should remain a user option
        if self.mode == CoreModeList.LISTENER_MODE:
            if self.__tm_listener.reply_event():
                LOGGER.info("TmTcHandler: Packets received.")
                packet_queues = self.__tm_listener.retrieve_tm_packet_queues(clear=True)
                if len(packet_queues) > 0:
                    self.__tm_handler.handle_packet_queues(
                        packet_queue_list=packet_queues
                    )
                self.__tm_listener.clear_reply_event()
        elif self.mode == CoreModeList.ONE_QUEUE_MODE:
            service_queue = self.__prepare_tc_queue()
            if service_queue is None:
                return
            LOGGER.info("Performing sequential command operation")
            # TODO: Some sort of reset mode for sequence handler? In total, we should request
            #       the queue from the user somehow and then handle it. After finishing the
            #       handling, request termination from the user. This mode will be optimized
            #       for handling a single queue, so the default behaviour should be to handle
            #       the queue and then request program termination. Alternatively, the user should
            #       be able to switch the mode
            self._seq_handler.queue_wrapper = service_queue
            self._seq_handler.send_queue_tc_and_receive_tm_sequentially()
            self.mode = CoreModeList.LISTENER_MODE
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
        service_queue = self.__tc_handler.feed_cb(self.current_proc_info)
        if not self.__com_if.valid:
            return None
        return service_queue
