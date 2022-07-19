#!/usr/bin/env python3
"""Example application for the TMTC Commander"""
import sys
import time
from typing import Optional

import tmtccmd
from spacepackets.ecss import PusTelemetry, PusTelecommand, PusVerificator
from spacepackets.ecss.pus_1_verification import UnpackParams

from tmtccmd import CcsdsTmtcBackend, TcHandlerBase
from tmtccmd.pus import VerificationWrapper
from tmtccmd.tm import CcsdsTmHandler, SpecificApidHandlerBase
from tmtccmd.com_if import ComInterface
from tmtccmd.config import (
    default_json_path,
    SetupParams,
    TmTcCfgHookBase,
    TmTcDefWrapper,
    CoreServiceList,
)
from tmtccmd.config import ArgParserWrapper, SetupWrapper
from tmtccmd.core import BackendController, BackendRequest
from tmtccmd.logging import get_console_logger
from tmtccmd.logging.pus import (
    RegularTmtcLogWrapper,
    RawTmtcTimedLogWrapper,
    TimedLogWhen,
)
from tmtccmd.tc import (
    QueueEntryHelper,
    TcQueueEntryType,
    ProcedureHelper,
    TcProcedureType,
    FeedWrapper,
)
from tmtccmd.tm.pus_5_event import Service5Tm
from tmtccmd.tm.pus_17_test import Service17TmExtended
from tmtccmd.tm.pus_1_verification import Service1TmExtended
from tmtccmd.util import FileSeqCountProvider
from tmtccmd.util.obj_id import ObjectIdDictT

from tmtccmd.util.tmtc_printer import FsfwTmTcPrinter

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


class PusHandler(SpecificApidHandlerBase):
    def __init__(
        self,
        verif_wrapper: VerificationWrapper,
        printer: FsfwTmTcPrinter,
        raw_logger: RawTmtcTimedLogWrapper,
    ):
        super().__init__(EXAMPLE_APID, None)
        self.printer = printer
        self.raw_logger = raw_logger
        self.verif_wrapper = verif_wrapper

    def handle_tm(self, packet: bytes, _user_args: any):
        try:
            tm_packet = PusTelemetry.unpack(packet)
        except ValueError:
            LOGGER.warning("Could not generate PUS TM object from raw data")
            LOGGER.warning(f"Raw Packet: [{packet.hex(sep=',')}], REPR: {packet!r}")
            return
        service = tm_packet.service
        dedicated_handler = False
        if service == 1:
            tm_packet = Service1TmExtended.unpack(
                data=packet, params=UnpackParams(1, 1)
            )
            res = self.verif_wrapper.add_tm(tm_packet)
            if res is None:
                LOGGER.info(
                    f"Received Verification TM[{tm_packet.service}, {tm_packet.subservice}] "
                    f"with Request ID {tm_packet.tc_req_id.as_u32():#08x}"
                )
                LOGGER.warning(
                    f"No matching telecommand found for {tm_packet.tc_req_id}"
                )
            else:
                self.verif_wrapper.log_to_console(tm_packet, res)
                self.verif_wrapper.log_to_file(tm_packet, res)
            dedicated_handler = True
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
        if not dedicated_handler and tm_packet is not None:
            self.printer.handle_long_tm_print(packet_if=tm_packet, info_if=tm_packet)


class TcHandler(TcHandlerBase):
    def __init__(
        self,
        seq_count_provider: FileSeqCountProvider,
        verif_wrapper: VerificationWrapper,
    ):
        super(TcHandler, self).__init__()
        self.seq_count_provider = seq_count_provider
        self.verif_wrapper = verif_wrapper

    def send_cb(self, entry_helper: QueueEntryHelper, com_if: ComInterface):
        if entry_helper.is_tc:
            if entry_helper.entry_type == TcQueueEntryType.PUS_TC:
                pus_tc_wrapper = entry_helper.to_pus_tc_entry()
                pus_tc_wrapper.pus_tc.seq_count = (
                    self.seq_count_provider.get_and_increment()
                )
                self.verif_wrapper.add_tc(pus_tc_wrapper.pus_tc)
                raw_tc = pus_tc_wrapper.pus_tc.pack()
                LOGGER.info(f"Sending {pus_tc_wrapper.pus_tc}")
                com_if.send(raw_tc)
        elif entry_helper.entry_type == TcQueueEntryType.LOG:
            log_entry = entry_helper.to_log_entry()
            LOGGER.info(log_entry.log_str)

    def queue_finished_cb(self, helper: ProcedureHelper):
        if helper.proc_type == TcProcedureType.DEFAULT:
            def_proc = helper.to_def_procedure()
            LOGGER.info(
                f"Queue handling finished for service {def_proc.service} and "
                f"op code {def_proc.op_code}"
            )

    def feed_cb(self, helper: ProcedureHelper, wrapper: FeedWrapper):
        if helper.proc_type == TcProcedureType.DEFAULT:
            def_proc = helper.to_def_procedure()
            queue_helper = wrapper.queue_helper
            service = def_proc.service
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
    verificator = PusVerificator()
    verification_wrapper = VerificationWrapper(verificator, LOGGER, printer.file_logger)
    # Create primary TM handler and add it to the CCSDS Packet Handler
    tm_handler = PusHandler(verification_wrapper, printer, raw_logger)
    ccsds_handler = CcsdsTmHandler(generic_handler=None)
    ccsds_handler.add_apid_handler(tm_handler)

    # Create TC handler
    seq_count_provider = FileSeqCountProvider()
    tc_handler = TcHandler(seq_count_provider, verification_wrapper)
    tmtccmd.setup(setup_args=setup_args)

    tmtc_backend = tmtccmd.create_default_tmtc_backend(
        setup_wrapper=setup_args, tm_handler=ccsds_handler, tc_handler=tc_handler
    )
    tmtccmd.start(tmtc_backend=tmtc_backend, hook_obj=hook_obj)
    ctrl = BackendController()
    try:
        while True:
            state = tmtc_backend.periodic_op(ctrl)
            if state.request == BackendRequest.TERMINATION_NO_ERROR:
                sys.exit(0)
            elif state.request == BackendRequest.DELAY_IDLE:
                LOGGER.info("TMTC Client in IDLE mode")
                time.sleep(3.0)
            elif state.request == BackendRequest.DELAY_LISTENER:
                time.sleep(0.8)
            elif state.request == BackendRequest.DELAY_CUSTOM:
                time.sleep(state.next_delay)
            elif state.request == BackendRequest.CALL_NEXT:
                pass
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    main()
