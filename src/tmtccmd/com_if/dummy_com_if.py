"""
@file   tmtcc_dummy_com_if.py
@date   09.03.2020
@brief  DUMMY Communication Interface

@author R. Mueller
"""
from typing import Tuple, cast

from tmtccmd.com_if.com_interface_base import CommunicationInterface
from tmtccmd.ecss.tc import PusTelecommand
from tmtccmd.pus_tm.factory import PusTelemetryFactory
from tmtccmd.pus_tm.service_1_verification import Service1TmPacked
from tmtccmd.utility.tmtcc_logger import get_logger

LOGGER = get_logger()


class DummyComIF(CommunicationInterface):
    def __init__(self, tmtc_printer):
        super().__init__(tmtc_printer)
        self.dummy_handler = DummyHandler()
        self.service_sent = 0
        self.reply_pending = False
        self.ssc = 0
        self.tc_ssc = 0
        self.tc_packet_id = 0

    def initialize(self) -> any:
        pass

    def open(self):
        pass

    def close(self) -> None:
        pass

    def data_available(self, parameters):
        if self.reply_pending:
            return True
        return False

    def poll_interface(self, parameters: any = 0) -> Tuple[bool, list]:
        pass

    def send_data(self, data: bytearray):
        pass

    def receive_telemetry(self, parameters: any = 0):
        tm_list = []
        if (self.service_sent == 17 or self.service_sent == 5) and self.reply_pending:
            LOGGER.info("dummy_com_if: Receive function called")
            tm_packer = Service1TmPacked(subservice=1, ssc=self.ssc, tc_packet_id=self.tc_packet_id,
                                         tc_ssc=self.tc_ssc)

            tm_packet_raw = tm_packer.pack()
            tm_packet = PusTelemetryFactory.create(tm_packet_raw)
            tm_list.append(tm_packet)
            tm_packer = Service1TmPacked(subservice=7, ssc=self.ssc, tc_packet_id=self.tc_packet_id,
                                         tc_ssc=self.tc_ssc)
            tm_packet_raw = tm_packer.pack()
            tm_packet = PusTelemetryFactory.create(tm_packet_raw)
            tm_list.append(tm_packet)
            self.reply_pending = False
            self.ssc += 1
        return tm_list

    def send_telecommand(self, tc_packet: bytearray, tc_packet_obj: PusTelecommand = None):
        if tc_packet_obj is not None:
            self.dummy_handler.pass_telecommand(pus_tc=tc_packet_obj)


class DummyHandler:
    def __init__(self):
        self.last_telecommand = None
        self.next_telemetry_package = []

    def pass_telecommand(self, pus_tc: PusTelecommand):
        self.last_telecommand = pus_tc

    def generate_reply_package(self):
        telecommand = cast(PusTelecommand, self.last_telecommand)
        if telecommand.get_service() == 17:
            if telecommand.get_subservice() == 1:
                pass

