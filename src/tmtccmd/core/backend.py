import atexit
import time
import sys
from threading import Thread
from abc import abstractmethod
from collections import deque
from typing import Tuple, Union

from tmtccmd.config.definitions import CoreComInterfaces, CoreGlobalIds, CoreServiceList, CoreModeList
from tmtccmd.utility.logger import get_logger
from tmtccmd.ecss.tc import PusTelecommand
from tmtccmd.sendreceive.single_command_sender_receiver import SingleCommandSenderReceiver
from tmtccmd.sendreceive.sequential_sender_receiver import SequentialCommandSenderReceiver
from tmtccmd.sendreceive.tm_listener import TmListener
from tmtccmd.com_if.com_interface_base import CommunicationInterface
from tmtccmd.utility.tmtc_printer import TmTcPrinter
from tmtccmd.pus_tc.packer import ServiceQueuePacker


LOGGER = get_logger()


class BackendBase:
    @abstractmethod
    def initialize(self):
        """
        Initialize the backend. Raise RuntimeError or ValueError on failure
        """

    @abstractmethod
    def start_listener(self):
        """
        Start the backend. Raise RuntimeError on failure
        """

    @abstractmethod
    def set_mode(self, mode: int):
        """
        Set backend mode
        :param mode:
        :return:
        """


class TmTcHandler(BackendBase):
    """
    This is the primary class which handles TMTC reception. This can be seen as the backend
    in case a GUI or front-end is implemented.
    """

    def __init__(
            self, com_if: CommunicationInterface, tmtc_printer: TmTcPrinter, tm_listener: TmListener,
            init_mode: int, init_service: Union[str, int] = CoreServiceList.SERVICE_17.value, init_opcode: str = "0"
    ):
        self.mode = init_mode
        self.com_if_key = com_if.get_id()
        self.__com_if_active = False
        self.__service = init_service
        self.__op_code = init_opcode

        # This flag could be used later to command the TMTC Client with a front-end
        self.one_shot_operation = True

        self.__com_if = com_if
        self.__tmtc_printer = tmtc_printer
        self.__tm_listener = tm_listener
        self.exit_on_com_if_init_failure = True

        self.single_command_package: Tuple[bytearray, Union[None, PusTelecommand]] = \
            (bytearray(), None)

    def get_com_if_id(self):
        return self.com_if_key

    def get_com_if(self) -> CommunicationInterface:
        return self.__com_if

    def get_printer(self) -> TmTcPrinter:
        return self.__tmtc_printer

    def get_listener(self):
        return self.__tm_listener

    def set_com_if(self, com_if: CommunicationInterface):
        if not self.is_com_if_active():
            self.__com_if = com_if
            self.__tm_listener.set_com_if(self.__com_if)
        else:
            LOGGER.warning("Communication Interface is active and must be closed first before reassigning a new one")

    def is_com_if_active(self):
        return self.__com_if_active

    def set_one_shot_or_loop_handling(self, enable: bool):
        """
        Specify whether the perform_operation() call will only handle one action depending
        on the mode or keep listening for replies after handling an operation.
        """
        self.one_shot_operation = enable

    def set_mode(self, mode: int):
        """
        Set the mode which will determine what perform_operation does.
        """
        self.mode = mode

    def get_mode(self) -> int:
        return self.mode

    def set_service(self, service: Union[str, int]):
        self.__service = service

    def set_opcode(self, op_code: str):
        self.__op_code = op_code

    def get_service(self) -> Union[str, int]:
        return self.__service

    def get_opcode(self) -> str:
        return self.__op_code

    @staticmethod
    def prepare_tmtc_handler_start(
            init_com_if: int = CoreComInterfaces.DUMMY,
            init_mode: int = CoreModeList.LISTENER_MODE,
            init_service: int = CoreServiceList.SERVICE_17
    ):
        from multiprocessing import Process
        tmtc_handler = TmTcHandler(init_com_if, init_mode, init_service)
        tmtc_task = Process(target=TmTcHandler.start_handler, args=(tmtc_handler, ))
        return tmtc_task

    @staticmethod
    def start_handler(executed_handler):
        if not isinstance(executed_handler, TmTcHandler):
            LOGGER.error("Unexpected argument, should be TmTcHandler!")
            sys.exit(1)
        executed_handler.initialize()
        executed_handler.start_listener()

    def initialize(self):
        from tmtccmd.utility.exit_handler import keyboard_interrupt_handler
        """
        Perform initialization steps which might be necessary after class construction.
        This has to be called at some point before using the class!
        """
        atexit.register(keyboard_interrupt_handler, tmtc_backend=self, com_interface=self.__com_if)

    def start_listener(self, perform_op_immediately: bool = True):
        try:
            self.__com_if.open()
            self.__tm_listener.start()
            self.__com_if_active = True
        except IOError:
            LOGGER.error("Communication Interface could not be opened!")
            LOGGER.info("TM listener will not be started")
            if self.exit_on_com_if_init_failure:
                LOGGER.error("Closing TMTC commander..")
                self.__com_if.close()
                sys.exit(1)
        if perform_op_immediately:
            self.perform_operation()

    def close_listener(self, join : bool = False, join_timeout_seconds: float = 1.0):
        """
        Closes the TM listener and the communication interface. This is started in a separarate thread because
        the communication interface might still be busy. The completion can be checked with
        :meth:`tmtccmd.core.backend.is_com_if_active`. Alternatively, waiting on completion is possible by specifying
        the join argument and a timeout in floating point second.
        :param join:
        :param join_timeout_seconds:
        :return:
        """
        if self.__com_if_active:
            close_thread = Thread(target=self.__com_if_closing)
            close_thread.start()
            if join:
                close_thread.join(timeout=join_timeout_seconds)

    def perform_operation(self):
        """
        Periodic operation
        """
        try:
            self.__core_operation(self.one_shot_operation)
        except KeyboardInterrupt:
            LOGGER.info("Keyboard Interrupt.")
            sys.exit()
        except IOError:
            LOGGER.exception("IO Error occured")
            sys.exit()

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
        """
        Command handling.
        """

        if self.mode == CoreModeList.LISTENER_MODE:
            if self.__tm_listener.reply_event():
                LOGGER.info("TmTcHandler: Packets received.")
                self.__tmtc_printer.print_telemetry_queue(self.__tm_listener.retrieve_tm_packet_queue())
                self.__tm_listener.clear_tm_packet_queue()
                self.__tm_listener.clear_reply_event()
        elif self.mode == CoreModeList.SEQUENTIAL_CMD_MODE:
            from tmtccmd.core.globals_manager import get_global
            service_queue = deque()
            service_queue_packer = ServiceQueuePacker()
            service_queue_packer.pack_service_queue_core(
                service=self.__service, service_queue=service_queue, op_code=self.__op_code)
            if not self.__com_if.valid:
                return
            LOGGER.info("Performing service command operation")
            sender_and_receiver = SequentialCommandSenderReceiver(
                com_if=self.__com_if, tmtc_printer=self.__tmtc_printer,
                tm_listener=self.__tm_listener, tc_queue=service_queue
            )
            sender_and_receiver.send_queue_tc_and_receive_tm_sequentially()
            self.mode = CoreModeList.LISTENER_MODE
        else:
            try:
                from tmtccmd.config.hook import get_global_hook_obj
                hook_obj = get_global_hook_obj()
                hook_obj.perform_mode_operation(mode=self.mode, tmtc_backend=self)
            except ImportError as error:
                print(error)
                LOGGER.error("Custom mode handling module not provided!")

    def __core_operation(self, one_shot):
        if self.mode == CoreModeList.LISTENER_MODE:
            one_shot = False
        if not one_shot:
            while True:
                self.__handle_action()
                if self.mode == CoreModeList.IDLE:
                    LOGGER.info("TMTC Client in idle mode")
                    time.sleep(5)
                elif self.mode == CoreModeList.LISTENER_MODE:
                    time.sleep(1)
        else:
            self.__handle_action()
