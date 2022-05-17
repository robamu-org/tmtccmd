#!/usr/bin/python3.8
"""
@file
    tmtcc_config.py
@date
    01.11.2019
@brief
    Used to send single tcs and listen for replies after that
"""
from typing import Optional, Tuple

from tmtccmd.ccsds.handler import CcsdsTmHandler
from tmtccmd.config.definitions import UsrSendCbT
from tmtccmd.sendreceive.cmd_sender_receiver import CommandSenderReceiver
from tmtccmd.sendreceive.tm_listener import TmListener
from tmtccmd.com_if.com_interface_base import CommunicationInterface

from tmtccmd.logging import get_console_logger

from tmtccmd.tc.definitions import PusTcTupleT


logger = get_console_logger()


class SingleCommandSenderReceiver(CommandSenderReceiver):
    """
    Specific implementation of CommandSenderReceiver to send a single telecommand
    This object can be used by instantiating it and calling sendSingleTcAndReceiveTm()
    """

    def __init__(
        self,
        com_if: CommunicationInterface,
        tm_listener: TmListener,
        tm_handler: CcsdsTmHandler,
        apid: int,
        usr_send_wrapper: Optional[Tuple[UsrSendCbT, any]] = None,
    ):
        """
        :param com_if: CommunicationInterface object, passed on to CommandSenderReceiver
        :param tm_listener: TmListener object which runs in the background and receives all TM
        """
        super().__init__(
            com_if=com_if,
            tm_listener=tm_listener,
            tm_handler=tm_handler,
            apid=apid,
            usr_send_wrapper=usr_send_wrapper,
        )

    def send_single_tc_and_receive_tm(self, pus_packet_tuple: PusTcTupleT):
        """
        Send a single telecommand passed to the class and wait for replies
        :return:
        """
        try:
            tuple_first, tuple_second = pus_packet_tuple
        except TypeError:
            logger.error("SingleCommandSenderReceiver: Invalid command input")
            return
        self._operation_pending = True
        self._tm_listener.sequence_mode()
        if self._usr_send_cb is not None:
            self._usr_send_cb(
                tuple_first, self._com_if, tuple_first, self._usr_send_args
            )
        else:
            self._com_if.send(tuple_first)
        # TODO: What if entry is not a telecommand?
        self._last_tc = tuple_first
        self._last_tc_obj = tuple_second
        while self._operation_pending:
            # wait until reply is received
            super()._check_for_first_reply()
        if self._reply_received:
            self._tm_listener.set_mode_op_finished()
            packet_queue = self._tm_listener.retrieve_ccsds_tm_packet_queue(
                apid=self._apid, clear=True
            )
            self._tm_handler.handle_ccsds_packet_queue(
                apid=self._apid, tm_queue=packet_queue
            )
            logger.info("SingleCommandSenderReceiver: Reply received")
            logger.info("Listening for packages ...")
