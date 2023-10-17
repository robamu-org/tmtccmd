from unittest import TestCase

from spacepackets.ccsds.time import CdsShortTimestamp
from spacepackets.ecss.tm import PusTelemetry
from tmtccmd.pus.s200_fsfw_mode import Subservice


class TestSrv200Tm(TestCase):
    def setUp(self):
        self.app_data = bytearray()
        self.app_data.extend(bytes([0x01, 0x02, 0x03, 0x04]))
        self.srv_200_tm = PusTelemetry(
            service=200,
            subservice=Subservice.TM_MODE_REPLY,
            time_provider=CdsShortTimestamp.empty(),
            apid=0x02,
        )
