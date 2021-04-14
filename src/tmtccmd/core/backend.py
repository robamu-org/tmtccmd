import atexit
import time
import sys
from collections import deque
from typing import Tuple, Union

from tmtccmd.core.definitions import CoreComInterfaces, CoreGlobalIds, CoreServiceList, CoreModeList
from tmtccmd.utility.tmtcc_logger import get_logger
from tmtccmd.ecss.tc import PusTelecommand
from tmtccmd.sendreceive.single_command_sender_receiver import SingleCommandSenderReceiver
from tmtccmd.sendreceive.sequential_sender_receiver import SequentialCommandSenderReceiver
from tmtccmd.sendreceive.tm_listener import TmListener
from tmtccmd.com_if.com_interface_base import CommunicationInterface
from tmtccmd.utility.tmtc_printer import TmTcPrinter
from tmtccmd.utility.exit_handler import keyboard_interrupt_handler
from tmtccmd.pus_tc.packer import ServiceQueuePacker

LOGGER = get_logger()


class TmTcHandler:
    """
    This is the primary class which handles TMTC reception. This can be seen as the backend
    in case a GUI or front-end is implemented.
    """

    def __init__(self, init_com_if: int, init_mode: int,
                 init_service: int, init_opcode: str = "0"):
        self.mode = init_mode
        self.com_if = init_com_if
        self.service = init_service
        self.op_code = init_opcode

        # This flag could be used later to command the TMTC Client with a front-end
        self.one_shot_operation = True

        self.tmtc_printer: Union[None, TmTcPrinter] = None
        self.communication_interface: Union[None, CommunicationInterface] = None
        self.tm_listener: Union[None, TmListener] = None
        self.exit_on_com_if_init_failure = True

        self.single_command_package: Tuple[bytearray, Union[None, PusTelecommand]] = \
            (bytearray(), None)

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

    def set_com_if(self, com_if: int):
        self.com_if = com_if

    def set_service(self, service: int):
        self.service = service

    def set_opcode(self, op_code: str):
        self.op_code = op_code

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
        executed_handler.start()

    def initialize(self):
        from tmtccmd.core.globals_manager import get_global
        from tmtccmd.core.hook_helper import get_global_hook_obj
        """
        Perform initialization steps which might be necessary after class construction.
        This has to be called at some point before using the class!
        """
        com_if = get_global(CoreGlobalIds.COM_IF)
        tc_send_timeout_factor = get_global(CoreGlobalIds.TC_SEND_TIMEOUT_FACTOR)
        tm_timeout = get_global(CoreGlobalIds.TM_TIMEOUT)
        display_mode = get_global(CoreGlobalIds.DISPLAY_MODE)
        print_to_file = get_global(CoreGlobalIds.PRINT_TO_FILE)
        self.tmtc_printer = TmTcPrinter(display_mode, print_to_file, True)
        hook_obj = get_global_hook_obj()
        self.communication_interface = hook_obj.assign_communication_interface(
            com_if=com_if, tmtc_printer=self.tmtc_printer
        )
        self.tm_listener = TmListener(
            com_interface=self.communication_interface, tm_timeout=tm_timeout,
            tc_timeout_factor=tc_send_timeout_factor
        )
        atexit.register(keyboard_interrupt_handler, com_interface=self.communication_interface)

    def start(self, perform_op_immediately: bool = True):
        try:
            self.communication_interface.open()
            self.tm_listener.start()
        except IOError:
            LOGGER.error("Communication Interface could not be opened!")
            LOGGER.info("TM listener will not be started")
            if self.exit_on_com_if_init_failure:
                LOGGER.error("Closing TMTC commander..")
                self.communication_interface.close()
                sys.exit(1)
        if perform_op_immediately:
            self.perform_operation()

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

    def __handle_action(self):
        """
        Command handling.
        """
        if self.mode == CoreModeList.PROMPT_MODE:
            self.prompt_mode()

        if self.mode == CoreModeList.LISTENER_MODE:
            if self.tm_listener.reply_event():
                LOGGER.info("TmTcHandler: Packets received.")
                self.tmtc_printer.print_telemetry_queue(self.tm_listener.retrieve_tm_packet_queue())
                self.tm_listener.clear_tm_packet_queue()
                self.tm_listener.clear_reply_event()

        elif self.mode == CoreModeList.SINGLE_CMD_MODE:
            pus_packet_tuple = None
            if self.single_command_package[1] is None:
                pus_command = command_preparation()
                if pus_command is not None:
                    pus_packet_tuple = pus_command.pack_command_tuple()
            else:
                pus_packet_tuple = self.single_command_package
            if pus_packet_tuple is not None:
                sender_and_receiver = SingleCommandSenderReceiver(
                    com_interface=self.communication_interface, tmtc_printer=self.tmtc_printer,
                    tm_listener=self.tm_listener)
                LOGGER.info("Performing single command operation..")
                sender_and_receiver.send_single_tc_and_receive_tm(pus_packet_tuple=pus_packet_tuple)
                self.mode = CoreModeList.PROMPT_MODE
            else:
                LOGGER.warning("No valid packet for single command mode found or set..")
        elif self.mode == CoreModeList.SEQUENTIAL_CMD_MODE:
            from tmtccmd.core.globals_manager import get_global
            service_queue = deque()
            service_queue_packer = ServiceQueuePacker()
            service_queue_packer.pack_service_queue_core(
                service=self.service, service_queue=service_queue, op_code=self.op_code)
            if not self.communication_interface.valid:
                return
            LOGGER.info("Performing service command operation")
            sender_and_receiver = SequentialCommandSenderReceiver(
                com_interface=self.communication_interface, tmtc_printer=self.tmtc_printer,
                tm_listener=self.tm_listener, tc_queue=service_queue)
            sender_and_receiver.send_queue_tc_and_receive_tm_sequentially()
            self.mode = CoreModeList.LISTENER_MODE

        elif self.mode == CoreModeList.SOFTWARE_TEST_MODE:
            from tmtccmd.core.hook_helper import get_global_hook_obj
            hook_obj = get_global_hook_obj()
            all_tc_queue = hook_obj.pack_total_service_queue()
            if all_tc_queue is None:
                LOGGER.warning("TC queue specified in user hook is None object.")
            else:
                LOGGER.info("Performing multiple service commands operation")
                sender_and_receiver = SequentialCommandSenderReceiver(
                    com_interface=self.communication_interface, tmtc_printer=self.tmtc_printer,
                    tc_queue=all_tc_queue, tm_listener=self.tm_listener)
                sender_and_receiver.send_queue_tc_and_receive_tm_sequentially()
                LOGGER.info("SequentialSenderReceiver: Exporting output to log file.")
                self.tmtc_printer.print_file_buffer_list_to_file("log/tmtc_log.txt", True)
        else:
            try:
                from tmtccmd.core.hook_helper import get_global_hook_obj
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

    def prompt_mode(self):
        next_mode = input("Please enter next mode (enter h for list of modes): ")
        if next_mode == 'h':
            print("Mode 0: Single Command Mode")
            print("Mode 1: Sequential Command Mode")
            print("Mode 2: Listener Mode")
            self.prompt_mode()
        elif next_mode == 1:
            self.mode = CoreModeList.LISTENER_MODE
        else:
            self.mode = CoreModeList.LISTENER_MODE

    # These two will not be used for now.
    # @staticmethod
    # def prepare_tmtc_handler_start_in_process(init_mode: ModeList):
    #    from multiprocessing import Process
    #    tmtc_handler_task = Process(target=TmTcHandler.start_tmtc_handler, args=(init_mode, ))
    #    return tmtc_handler_task

    # @staticmethod
    # def start_tmtc_handler(handler_args: any):
    #    tmtc_handler = TmTcHandler(handler_args)
    #    tmtc_handler.initialize()
    #    tmtc_handler.perform_operation()


def command_preparation() -> PusTelecommand:
    """
    Prepare command for single command testing
    :return:
    """
    try:
        from tmtccmd.core.hook_helper import get_global_hook_obj
        hook_obj = get_global_hook_obj()
        return hook_obj.command_preparation_hook()
    except ImportError as e:
        print(e)
        LOGGER.error("Hook function for command application not implemented!")
        sys.exit(1)
