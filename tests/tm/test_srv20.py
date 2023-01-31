from unittest import TestCase

from spacepackets.ecss import PusService
from tmtccmd.pus.s20_fsfw_param_defs import (
    create_scalar_boolean_parameter,
    CustomSubservice,
    Parameter,
)
from tmtccmd.tm.pus_20_fsfw_param import Service20FsfwTm, Service20ParamDumpWrapper


class TestSrv20Tm(TestCase):
    def setUp(self):
        self.obj_id = bytes([0x01, 0x02, 0x03, 0x04])
        self.boolean_param = create_scalar_boolean_parameter(
            object_id=self.obj_id, domain_id=1, unique_id=5, parameter=True
        )
        self.tm = Service20FsfwTm(
            subservice=CustomSubservice.TM_DUMP_REPLY,
            time_provider=None,
            source_data=self.boolean_param.pack(),
        )

    def test_state(self):
        self.assertEqual(self.tm.time_provider, None)
        self.assertEqual(self.tm.service, PusService.S20_PARAMETER)
        self.assertEqual(self.tm.subservice, CustomSubservice.TM_DUMP_REPLY)
        self.assertEqual(self.tm.source_data, self.boolean_param.pack())
        self.assertEqual(self.tm.object_id, self.obj_id)

    def test_unpack(self):
        tm_raw = self.tm.pack()
        tm_unpacked = Service20FsfwTm.unpack(raw_telemetry=tm_raw, time_reader=None)
        self.assertEqual(self.tm, tm_unpacked)
        param_unpacked = Parameter.unpack(tm_unpacked.source_data)
        self.assertEqual(param_unpacked, self.boolean_param)

    def test_dump_wrapper(self):
        self.dump_wrapper = Service20ParamDumpWrapper(param_tm=self.tm)
        param = self.dump_wrapper.get_param()
        self.assertEqual(param, self.boolean_param)
