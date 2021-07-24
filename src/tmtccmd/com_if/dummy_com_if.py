"""
:file:      dummy_com_if.py
:date:      09.03.2020
:brief:     Dummy Communication Interface. Currently serves to provide an example without external hardware
"""
from typing import cast

from tmtccmd.com_if.com_interface_base import CommunicationInterface
from tmtccmd.ecss.tc import PusTelecommand
from tmtccmd.tm.definitions import TelemetryListT
from tmtccmd.tm.service_1_verification import Service1TmPacked
from tmtccmd.tm.service_17_test import Service17TmPacked
from tmtccmd.pus.service_17_test import Srv17Subservices
from tmtccmd.utility.logger import get_console_logger
from tmtccmd.utility.tmtc_printer import TmTcPrinter

LOGGER = get_console_logger()


class DummyComIF(CommunicationInterface):
    def __init__(self, com_if_key: str, tmtc_printer: TmTcPrinter):
        super().__init__(com_if_key=com_if_key, tmtc_printer=tmtc_printer)
        self.dummy_handler = DummyHandler()
        self.last_service = 0
        self.last_subservice = 0
        self.tc_ssc = 0
        self.tc_packet_id = 0

    def initialize(self, args: any = None) -> any:
        pass

    def open(self, args: any = None) -> None:
        pass

    def close(self, args: any = None) -> None:
        pass

    def data_available(self, timeout: float = 0, parameters: any = 0):
        if self.dummy_handler.reply_pending:
            return True
        return False

    def receive(self, parameters: any = 0) -> TelemetryListT:
        return self.dummy_handler.receive_reply_package()

    def send(self, data: bytearray):
        if data is not None:
            self.dummy_handler.pass_telecommand(data=data)


class DummyHandler:
    def __init__(self):
        self.last_telecommand = None
        self.next_telemetry_package = []
        self.last_tc_ssc = 0
        self.last_tc_packet_id = 0
        self.current_ssc = 0
        self.reply_pending = False

    def pass_telecommand(self, data: bytearray):
        # TODO: Need TC deserializer for cleaner implementation
        self.last_telecommand = data
        self.last_tc_ssc = ((data[2] << 8) | data[3]) & 0x3fff
        self.last_service = data[7]
        self.last_subservice = data[8]
        self.tc_packet_id = data[0] << 8 | data[1]
        self.reply_pending = True
        self.generate_reply_package()

    def generate_reply_package(self):
        """
        Generate the replies. This function will perform the following steps:
         - Generate an object representation of the telemetry to be generated based on service and subservice
         - Generate the raw bytearray of the telemetry
         - Generate the object representation which would otherwise be generated from the raw bytearray received
           from an external source
        """
        if self.last_service == 17:
            if self.last_subservice == 1:
                tm_packer = Service1TmPacked(
                    subservice=1, ssc=self.current_ssc, tc_packet_id=self.last_tc_packet_id,
                    tc_ssc=self.last_tc_ssc
                )

                self.current_ssc += 1
                tm_packet_raw = tm_packer.pack()
                self.next_telemetry_package.append(tm_packet_raw)
                tm_packer = Service1TmPacked(
                    subservice=7, ssc=self.current_ssc, tc_packet_id=self.last_tc_packet_id,
                    tc_ssc=self.last_tc_ssc
                )
                tm_packet_raw = tm_packer.pack()
                self.next_telemetry_package.append(tm_packet_raw)
                self.current_ssc += 1

                tm_packer = Service17TmPacked(subservice=Srv17Subservices.PING_REPLY)
                tm_packet_raw = tm_packer.pack()
                self.next_telemetry_package.append(tm_packet_raw)
                self.current_ssc += 1

    def receive_reply_package(self) -> TelemetryListT:
        if self.reply_pending:
            return_list = self.next_telemetry_package.copy()
            self.next_telemetry_package.clear()
            self.reply_pending = False
            return return_list
        else:
            return []
