import struct
from unittest import TestCase

from spacepackets.ecss import RequestId, PusTelecommand, PacketFieldU8
from spacepackets.ecss.pus_1_verification import (
    Service1Tm,
    Subservice,
    VerificationParams,
    FailureNotice,
)
from tmtccmd.tm.pus_1_verification import Service1FsfwWrapper


class TestVerif1TmWrapper(TestCase):
    def setUp(self) -> None:
        self.ping_tc = PusTelecommand(service=17, subservice=1)
        pass

    def test_basic(self):
        context_param_1 = bytearray([0x10, 0x20, 0x30, 0x40])
        context_param_1_as_int = struct.unpack("!I", context_param_1)[0]
        context_param_2 = bytearray([0x40, 0x30, 0x20, 0x10])
        context_param_2_as_int = struct.unpack("!I", context_param_2)[0]
        failure_notice = FailureNotice(
            code=PacketFieldU8(1), data=context_param_1 + context_param_2
        )
        service_1_tm = Service1Tm(
            subservice=Subservice.TM_START_FAILURE,
            time_provider=None,
            verif_params=VerificationParams(
                step_id=None,
                req_id=RequestId.from_pus_tc(self.ping_tc),
                failure_notice=failure_notice,
            ),
        )
        wrapper = Service1FsfwWrapper(service_1_tm)
        self.assertEqual(wrapper.error_param_1, context_param_1_as_int)
        self.assertEqual(wrapper.error_param_2, context_param_2_as_int)
