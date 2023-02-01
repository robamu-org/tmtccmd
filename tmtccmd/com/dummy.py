"""Dummy Virtual Communication Interface. Currently serves to use the TMTC program without needing
external hardware or an extra socket
"""
from typing import Optional

from spacepackets.ecss.pus_17_test import Service17Tm
from spacepackets.ecss.pus_1_verification import (
    RequestId,
    VerificationParams,
    Service1Tm,
)
from spacepackets.ecss.tc import PusTelecommand
from spacepackets.ccsds.time import CdsShortTimestamp

from tmtccmd.com import ComInterface
from tmtccmd.config import CoreComInterfaces
from tmtccmd.tm import TelemetryListT
from tmtccmd.tm.pus_1_verification import Subservice as Pus1Subservices
from tmtccmd.tm.pus_17_test import Subservice as Pus17Subservices


class DummyHandler:
    def __init__(self):
        self.last_tc: Optional[PusTelecommand] = None
        self.next_telemetry_package = []
        self.current_ssc = 0
        self.reply_pending = False

    def pass_telecommand(self, data: bytearray):
        self.last_tc = PusTelecommand.unpack(data)
        self.reply_pending = True
        self.generate_reply_package()

    def generate_reply_package(self):
        """Generate a reply package. Currently, this only generates a reply for a ping
        telecommand."""
        if self.last_tc.service == 17:
            if self.last_tc.subservice == 1:
                current_time_stamp = CdsShortTimestamp.from_now()
                tm_packer = Service1Tm(
                    subservice=Pus1Subservices.TM_ACCEPTANCE_SUCCESS,
                    seq_count=self.current_ssc,
                    verif_params=VerificationParams(
                        req_id=RequestId(
                            self.last_tc.packet_id, self.last_tc.packet_seq_ctrl
                        )
                    ),
                    time_provider=current_time_stamp,
                )

                self.current_ssc += 1
                tm_packet_raw = tm_packer.pack()
                self.next_telemetry_package.append(tm_packet_raw)
                tm_packer = Service1Tm(
                    subservice=Pus1Subservices.TM_START_SUCCESS,
                    seq_count=self.current_ssc,
                    verif_params=VerificationParams(
                        req_id=RequestId(
                            self.last_tc.packet_id, self.last_tc.packet_seq_ctrl
                        )
                    ),
                    time_provider=current_time_stamp,
                )
                tm_packet_raw = tm_packer.pack()
                self.next_telemetry_package.append(tm_packet_raw)
                self.current_ssc += 1

                tm_packer = Service17Tm(
                    subservice=Pus17Subservices.TM_REPLY,
                    time_provider=current_time_stamp,
                )
                tm_packet_raw = tm_packer.pack()
                self.next_telemetry_package.append(tm_packet_raw)
                self.current_ssc += 1

                tm_packer = Service1Tm(
                    subservice=Pus1Subservices.TM_COMPLETION_SUCCESS,
                    seq_count=self.current_ssc,
                    verif_params=VerificationParams(
                        req_id=RequestId(
                            self.last_tc.packet_id, self.last_tc.packet_seq_ctrl
                        )
                    ),
                    time_provider=current_time_stamp,
                )
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


class DummyComIF(ComInterface):
    def __init__(self):
        self.com_if_id = CoreComInterfaces.DUMMY.value
        self.dummy_handler = DummyHandler()
        self._open = False
        self.initialized = False

    @property
    def id(self) -> str:
        return self.com_if_id

    def initialize(self, args: any = None) -> any:
        self.initialized = True

    def open(self, args: any = None) -> None:
        self._open = True

    def is_open(self) -> bool:
        return self._open

    def close(self, args: any = None) -> None:
        self._open = False

    def data_available(self, timeout: float = 0, parameters: any = 0):
        if self.dummy_handler.reply_pending:
            return True
        return False

    def receive(self, parameters: any = 0) -> TelemetryListT:
        return self.dummy_handler.receive_reply_package()

    def send(self, data: bytearray):
        if data is not None:
            self.dummy_handler.pass_telecommand(data)
