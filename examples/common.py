from typing import Optional

from pus_tc.service_17_test import pack_service17_test_into
from spacepackets.ecss import PusTelemetry
from tmtccmd import get_console_logger, TcHandlerBase, TmTcCfgHookBase, CcsdsTmtcBackend
from tmtccmd.ccsds.handler import ApidTmHandlerBase
from tmtccmd.com_if.com_interface_base import CommunicationInterface
from tmtccmd.config import CoreServiceList
from tmtccmd.config.tmtc_defs import TmTcDefWrapper
from tmtccmd.logging.pus import RawTmtcTimedLogWrapper
from tmtccmd.tc import (
    TcProcedureBase,
    TcQueueEntryBase,
    PacketCastWrapper,
    TcQueueEntryType, ProcedureCastWrapper, TcProcedureType,
)
from tmtccmd.tc.handler import FeedWrapper
from tmtccmd.tm import Service5Tm
from tmtccmd.tm.pus_17_test import Service17TMExtended
from tmtccmd.utility.obj_id import ObjectIdDictT
from tmtccmd.utility.tmtc_printer import FsfwTmTcPrinter

APID = 0xEF
LOGGER = get_console_logger()


class ExampleHookClass(TmTcCfgHookBase):
    def __init__(self, json_cfg_path: str):
        super().__init__(json_cfg_path=json_cfg_path)

    def assign_communication_interface(
        self, com_if_key: str
    ) -> Optional[CommunicationInterface]:
        from tmtccmd.config.com_if import create_communication_interface_default

        LOGGER.info("Communication interface assignment function was called")
        return create_communication_interface_default(
            com_if_key=com_if_key,
            json_cfg_path=self.json_cfg_path,
        )

    def get_tmtc_definitions(self) -> TmTcDefWrapper:
        from tmtccmd.config.globals import get_default_tmtc_defs

        return get_default_tmtc_defs()

    def perform_mode_operation(self, tmtc_backend: CcsdsTmtcBackend, mode: int):
        LOGGER.info("Mode operation hook was called")
        pass

    def get_object_ids(self) -> ObjectIdDictT:
        from tmtccmd.config.objects import get_core_object_ids

        return get_core_object_ids()


class PusHandler(ApidTmHandlerBase):
    def __init__(self, printer: FsfwTmTcPrinter, raw_logger: RawTmtcTimedLogWrapper):
        super().__init__(APID, None)
        self.printer = printer
        self.raw_logger = raw_logger

    def handle_tm(self, packet: bytes, _user_args: any):
        try:
            tm_packet = PusTelemetry.unpack(packet)
        except ValueError:
            LOGGER.warning("Could not generate PUS TM object from raw data")
            LOGGER.warning(f"Raw Packet: [{packet.hex(sep=',')}], REPR: {packet!r}")
            return
        service = tm_packet.service
        if service == 1:
            tm_packet = Service17TMExtended.unpack(packet)
        if service == 5:
            tm_packet = Service5Tm.unpack(packet)
        if service == 17:
            tm_packet = Service17TMExtended.unpack(packet)
        if tm_packet is None:
            LOGGER.info(
                f"The service {service} is not implemented in Telemetry Factory"
            )
            tm_packet = PusTelemetry.unpack(packet)
        self.raw_logger.log_tm(tm_packet)
        self.printer.handle_long_tm_print(packet_if=tm_packet, info_if=tm_packet)


class TcHandler(TcHandlerBase):
    def send_cb(self, tc_queue_entry: TcQueueEntryBase, com_if: CommunicationInterface):
        cast_wrapper = PacketCastWrapper(tc_queue_entry)
        if tc_queue_entry.is_tc():
            if tc_queue_entry.etype == TcQueueEntryType.PUS_TC:
                pus_tc_wrapper = cast_wrapper.to_pus_tc_entry()
                raw_tc = pus_tc_wrapper.pus_tc.pack()
                LOGGER.info(f"Sending {pus_tc_wrapper.pus_tc}")
                com_if.send(raw_tc)

    def queue_finished_cb(self, info: TcProcedureBase):
        pass

    def feed_cb(self, info: TcProcedureBase, wrapper: FeedWrapper):
        proc_caster = ProcedureCastWrapper(info)
        if info.ptype == TcProcedureType.DEFAULT:
            info = proc_caster.to_def_procedure()
            queue_helper = wrapper.queue_helper
            service = info.service
            op_code = info.op_code
            if service == CoreServiceList.SERVICE_17.value:
                return pack_service17_test_into(queue_helper, op_code=op_code)
