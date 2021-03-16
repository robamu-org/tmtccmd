#!/usr/bin/python3.8
"""
@file
    tmtcc_config.py
@date
    01.11.2019
@brief
    Used to send single tcs and listen for replies after that
"""

from tmtccmd.sendreceive.cmd_sender_receiver import CommandSenderReceiver
from tmtccmd.sendreceive.tm_listener import TmListener

from tmtccmd.com_if.com_interface_base import CommunicationInterface

from tmtccmd.utility.tmtcc_tmtc_printer import TmTcPrinter
from tmtccmd.utility.tmtcc_logger import get_logger

from tmtccmd.pus_tc.base import PusTcTupleT


logger = get_logger()


class SingleCommandSenderReceiver(CommandSenderReceiver):
    """
    Specific implementation of CommandSenderReceiver to send a single telecommand
    This object can be used by instantiating it and calling sendSingleTcAndReceiveTm()
    """
    def __init__(self, com_interface: CommunicationInterface, tmtc_printer: TmTcPrinter,
                 tm_listener: TmListener):
        """
        :param com_interface: CommunicationInterface object, passed on to CommandSenderReceiver
        :param tm_listener: TmListener object which runs in the background and receives all TM
        :param tmtc_printer: TmTcPrinter object, passed on to CommandSenderReceiver
        """
        super().__init__(com_interface=com_interface, tm_listener=tm_listener,
                         tmtc_printer=tmtc_printer)

    def send_single_tc_and_receive_tm(self, pus_packet_tuple: PusTcTupleT):
        """
        Send a single telecommand passed to the class and wait for replies
        :return:
        """
        try:
            pus_packet, pus_packet_info = pus_packet_tuple
        except TypeError:
            logger.error("SingleCommandSenderReceiver: Invalid command input")
            return
        self._operation_pending = True
        self._tm_listener.set_listener_mode(TmListener.ListenerModes.SEQUENCE)
        self._tmtc_printer.print_telecommand(pus_packet, pus_packet_info)
        self._com_interface.send_telecommand(pus_packet, pus_packet_info)
        self._last_tc = pus_packet
        self._last_tc_info = pus_packet_info
        while self._operation_pending:
            # wait until reply is received
            super()._check_for_first_reply()
        if self._reply_received:
            self._tm_listener.event_mode_op_finished.set()
            self.print_tm_queue(self._tm_listener.retrieve_tm_packet_queue())
            logger.info("SingleCommandSenderReceiver: Reply received")
            logger.info("Listening for packages ...")