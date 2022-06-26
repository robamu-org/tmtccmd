#!/usr/bin/env python3
"""Example application for the TMTC Commander"""
import sys
import time
from typing import Optional

import tmtccmd
from spacepackets.ecss import PusTelemetry, PusTelecommand

from tmtccmd import CcsdsTmtcBackend, TcHandlerBase
from tmtccmd.ccsds.handler import CcsdsTmHandler, ApidTmHandlerBase
from tmtccmd.com_if import ComInterface
from tmtccmd.config import (
    default_json_path,
    SetupParams,
    TmTcCfgHookBase,
    TmTcDefWrapper,
    CoreServiceList,
)
from tmtccmd.config import ArgParserWrapper, SetupWrapper
from tmtccmd.core import BackendController, Request
from tmtccmd.logging import get_console_logger
from tmtccmd.logging.pus import (
    RegularTmtcLogWrapper,
    RawTmtcTimedLogWrapper,
    TimedLogWhen,
)
from tmtccmd.tc import (
    TcQueueEntryBase,
    PacketCastWrapper,
    TcQueueEntryType,
    TcProcedureBase,
    ProcedureCastWrapper,
    TcProcedureType,
)
from tmtccmd.tc.handler import FeedWrapper
from tmtccmd.tm import Service5Tm
from tmtccmd.tm.pus_17_test import Service17TmExtended
from tmtccmd.tm.pus_1_verification import Service1TmExtended
from tmtccmd.utility.obj_id import ObjectIdDictT

from tmtccmd.utility.tmtc_printer import FsfwTmTcPrinter

LOGGER = get_console_logger()
EXAMPLE_APID = 0xEF


class ExampleHookClass(TmTcCfgHookBase):
    def __init__(self, json_cfg_path: str):
        super().__init__(json_cfg_path=json_cfg_path)

    def assign_communication_interface(self, com_if_key: str) -> Optional[ComInterface]:
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
        super().__init__(EXAMPLE_APID, None)
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
            tm_packet = Service1TmExtended.unpack(packet)
        if service == 5:
            tm_packet = Service5Tm.unpack(packet)
        if service == 17:
            tm_packet = Service17TmExtended.unpack(packet)
        if tm_packet is None:
            LOGGER.info(
                f"The service {service} is not implemented in Telemetry Factory"
            )
            tm_packet = PusTelemetry.unpack(packet)
        self.raw_logger.log_tm(tm_packet)
        self.printer.handle_long_tm_print(packet_if=tm_packet, info_if=tm_packet)


class TcHandler(TcHandlerBase):
    def send_cb(self, tc_queue_entry: TcQueueEntryBase, com_if: ComInterface):
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
            if service == CoreServiceList.SERVICE_17.value:
                return queue_helper.add_pus_tc(PusTelecommand(service=17, subservice=1))


def main():
    tmtccmd.init_printout(False)
    hook_obj = ExampleHookClass(json_cfg_path=default_json_path())
    parser_wrapper = ArgParserWrapper(hook_obj)
    parser_wrapper.parse()
    params = SetupParams()
    parser_wrapper.set_params(params)
    params.apid = EXAMPLE_APID
    setup_args = SetupWrapper(hook_obj=hook_obj, setup_params=params)
    # Create console logger helper and file loggers
    tmtc_logger = RegularTmtcLogWrapper()
    printer = FsfwTmTcPrinter(tmtc_logger.logger)
    raw_logger = RawTmtcTimedLogWrapper(when=TimedLogWhen.PER_HOUR, interval=1)

    # Create primary TM handler and add it to the CCSDS Packet Handler
    tm_handler = PusHandler(printer, raw_logger)
    ccsds_handler = CcsdsTmHandler(unknown_handler=None)
    ccsds_handler.add_apid_handler(tm_handler)

    # Create TC handler
    tc_handler = TcHandler()
    tmtccmd.setup(setup_args=setup_args)

    tmtc_backend = tmtccmd.create_default_tmtc_backend(
        setup_wrapper=setup_args, tm_handler=ccsds_handler, tc_handler=tc_handler
    )
    tmtccmd.start(tmtc_backend=tmtc_backend)
    ctrl = BackendController()
    try:
        while True:
            state = tmtc_backend.periodic_op(ctrl)
            if state.request == Request.TERMINATION_NO_ERROR:
                sys.exit(0)
            elif state.request == Request.DELAY_IDLE:
                LOGGER.info("TMTC Client in IDLE mode")
                time.sleep(3.0)
            elif state.request == Request.DELAY_LISTENER:
                time.sleep(0.8)
            elif state.request == Request.DELAY_CUSTOM:
                time.sleep(state.next_delay)
            elif state.request == Request.CALL_NEXT:
                pass
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    main()
