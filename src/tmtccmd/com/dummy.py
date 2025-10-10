"""Dummy Virtual Communication Interface. Currently serves to use the TMTC program without needing
external hardware or an extra socket
"""

from __future__ import annotations

from typing import Any, Optional

from spacepackets.ccsds.time import CdsShortTimestamp
from spacepackets.ecss.pus_1_verification import (
    RequestId,
    Service1Tm,
    VerificationParams,
)
from spacepackets.ecss.pus_17_test import Service17Tm
from spacepackets.ecss.tc import PusTelecommand

from com_interface import ComInterface
from tmtccmd.config import CoreComInterfaces
from tmtccmd.pus.s1_verification import Subservice as Pus1Subservice
from tmtccmd.pus.s17_test import Subservice as Pus17Subservice
from tmtccmd.tmtc import TelemetryListT


class DummyHandler:
    def __init__(self):
        self.last_tc: Optional[PusTelecommand] = None
        self.next_telemetry_package = []
        self.current_ssc = 0
        self.reply_pending = False

    def insert_telecommand(self, data: bytearray | bytes):
        self.last_tc = PusTelecommand.unpack(data)
        self.reply_pending = True
        self.generate_reply_package()

    def generate_reply_package(self):
        """Generate a reply package. Currently, this only generates a reply for a ping
        telecommand."""
        assert self.last_tc is not None
        if self.last_tc.service == 17:
            if self.last_tc.subservice == 1:
                current_time_stamp = CdsShortTimestamp.now()
                tm_packer = Service1Tm(
                    subservice=Pus1Subservice.TM_ACCEPTANCE_SUCCESS,
                    apid=self.last_tc.apid,
                    seq_count=self.current_ssc,
                    verif_params=VerificationParams(
                        req_id=RequestId(self.last_tc.packet_id, self.last_tc.packet_seq_control)
                    ),
                    timestamp=current_time_stamp.pack(),
                )

                self.current_ssc += 1
                tm_packet_raw = tm_packer.pack()
                self.next_telemetry_package.append(tm_packet_raw)
                tm_packer = Service1Tm(
                    subservice=Pus1Subservice.TM_START_SUCCESS,
                    apid=self.last_tc.apid,
                    seq_count=self.current_ssc,
                    verif_params=VerificationParams(
                        req_id=RequestId(self.last_tc.packet_id, self.last_tc.packet_seq_control)
                    ),
                    timestamp=current_time_stamp.pack(),
                )
                tm_packet_raw = tm_packer.pack()
                self.next_telemetry_package.append(tm_packet_raw)
                self.current_ssc += 1

                tm_packer = Service17Tm(
                    subservice=Pus17Subservice.TM_REPLY,
                    apid=self.last_tc.apid,
                    timestamp=current_time_stamp.pack(),
                )
                tm_packet_raw = tm_packer.pack()
                self.next_telemetry_package.append(tm_packet_raw)
                self.current_ssc += 1

                tm_packer = Service1Tm(
                    subservice=Pus1Subservice.TM_COMPLETION_SUCCESS,
                    apid=self.last_tc.apid,
                    seq_count=self.current_ssc,
                    verif_params=VerificationParams(
                        req_id=RequestId(self.last_tc.packet_id, self.last_tc.packet_seq_control)
                    ),
                    timestamp=current_time_stamp.pack(),
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


class DummyInterface(ComInterface):
    def __init__(self):
        self.com_if_id = CoreComInterfaces.DUMMY.value
        self.dummy_handler = DummyHandler()
        self._open = False
        self.initialized = False

    @property
    def id(self) -> str:
        return self.com_if_id

    def initialize(self, args: Any = None) -> None:
        self.initialized = True

    def open(self, args: Any = None) -> None:
        self._open = True

    def is_open(self) -> bool:
        return self._open

    def close(self, args: Any = None) -> None:
        self._open = False

    def receive(self, parameters: Any = 0) -> list[bytes]:
        """Returns a list of received packets. The child class can use a separate thread to poll for
        the packets or use some other mechanism and container like a deque to store packets
        to be returned here.

        :param parameters:
        :raises ReceptionDecodeError: If the underlying COM interface uses encoding and
            decoding and the decoding fails, this exception will be returned.
        :return:
        """
        return self.dummy_handler.receive_reply_package()

    def packets_available(self, parameters: Any = 0) -> int:
        """Poll whether packets are available.

        :param parameters: Can be an arbitrary parameter.
        :raises ReceptionDecodeError: If the underlying COM interface uses encoding and
            decoding when determining the number of available packets, this exception can be
            thrown on decoding errors.
        :return: Number of packets available.
        """
        if self.dummy_handler.reply_pending:
            return True
        return False

    def send(self, data: bytes | bytearray):
        if data is not None:
            self.dummy_handler.insert_telecommand(data)
