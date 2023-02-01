#!/usr/bin/env python3
"""Example application for the TMTC Commander"""
import logging
import sys
import time
from typing import Optional

import tmtccmd
from spacepackets.ccsds import CdsShortTimestamp
from spacepackets.ecss import PusTelemetry, PusTelecommand, PusVerificator
from spacepackets.ecss.pus_17_test import Service17Tm
from spacepackets.ecss.pus_1_verification import UnpackParams, Service1Tm
from spacepackets.util import UnsignedByteField

from tmtccmd import CcsdsTmtcBackend, ProcedureParamsWrapper, BackendRequest
from tmtccmd.com import ComInterface
from tmtccmd.pus import VerificationWrapper
from tmtccmd.tm import CcsdsTmHandler, SpecificApidHandlerBase
from tmtccmd.config import (
    default_json_path,
    SetupParams,
    HookBase,
    TmtcDefinitionWrapper,
    CoreServiceList,
    OpCodeEntry,
    params_to_procedure_conversion,
    PreArgsParsingWrapper,
    SetupWrapper,
)
from tmtccmd.logging import add_colorlog_console_logger
from tmtccmd.logging.pus import (
    RegularTmtcLogWrapper,
    RawTmtcTimedLogWrapper,
    TimedLogWhen,
)
from tmtccmd.tc import (
    TcQueueEntryType,
    ProcedureWrapper,
    TcProcedureType,
    FeedWrapper,
    SendCbParams,
    DefaultPusQueueHelper,
    TcHandlerBase,
    QueueWrapper,
)
from tmtccmd.tm.pus_5_fsfw_event import Service5Tm
from tmtccmd.util import FileSeqCountProvider, PusFileSeqCountProvider, ObjectIdDictT
from tmtccmd.util.tmtc_printer import FsfwTmTcPrinter

_LOGGER = logging.getLogger()

EXAMPLE_PUS_APID = 0xEF
EXAMPLE_CFDP_APID = 0xF0

CFDP_LOCAL_ENTITY_ID = UnsignedByteField(byte_len=2, val=1)
CFDP_REMOTE_ENTITY_ID = UnsignedByteField(byte_len=2, val=EXAMPLE_CFDP_APID)


class ExampleHookClass(HookBase):
    def __init__(self, json_cfg_path: str):
        super().__init__(json_cfg_path=json_cfg_path)

    def assign_communication_interface(self, com_if_key: str) -> Optional[ComInterface]:
        print("Communication interface assignment function was called")
        from tmtccmd.config.com import (
            create_com_interface_default,
            create_com_interface_cfg_default,
        )

        cfg = create_com_interface_cfg_default(
            com_if_key=com_if_key,
            json_cfg_path=self.cfg_path,
            space_packet_ids=None,
        )
        return create_com_interface_default(cfg)

    def get_tmtc_definitions(self) -> TmtcDefinitionWrapper:
        from tmtccmd.config.globals import get_default_tmtc_defs

        defs = get_default_tmtc_defs()
        srv_5 = OpCodeEntry()
        srv_5.add("0", "Event Test")
        defs.add_service(
            name=CoreServiceList.SERVICE_5.value,
            info="PUS Service 5 Event",
            op_code_entry=srv_5,
        )
        srv_17 = OpCodeEntry()
        srv_17.add("0", "Ping Test")
        defs.add_service(
            name=CoreServiceList.SERVICE_17_ALT,
            info="PUS Service 17 Test",
            op_code_entry=srv_17,
        )
        return defs

    def perform_mode_operation(self, tmtc_backend: CcsdsTmtcBackend, mode: int):
        _LOGGER.info("Mode operation hook was called")
        pass

    def get_object_ids(self) -> ObjectIdDictT:
        from tmtccmd.config.objects import get_core_object_ids

        return get_core_object_ids()


class DualLogger:
    def __init__(self, file_logger: logging.Logger, console_logger: logging.Logger):
        self.file_logger = file_logger
        self.console_logger = console_logger

    def info(self, string: str):
        self.console_logger.info(string)
        self.file_logger.info(string)

    def print(self, string: str):
        print(string)
        self.file_logger.info(string)


class PusTmHandler(SpecificApidHandlerBase):
    def __init__(
        self,
        verif_wrapper: VerificationWrapper,
        printer: FsfwTmTcPrinter,
        raw_logger: RawTmtcTimedLogWrapper,
    ):
        super().__init__(EXAMPLE_PUS_APID, None)
        self.printer = printer
        self.raw_logger = raw_logger
        self.verif_wrapper = verif_wrapper
        self.dlogger = DualLogger(self.printer.file_logger, _LOGGER)

    def handle_tm(self, packet: bytes, _user_args: any):
        try:
            tm_packet = PusTelemetry.unpack(
                packet, time_reader=CdsShortTimestamp.empty()
            )
        except ValueError as e:
            _LOGGER.warning("Could not generate PUS TM object from raw data")
            _LOGGER.warning(f"Raw Packet: [{packet.hex(sep=',')}], REPR: {packet!r}")
            raise e
        service = tm_packet.service
        dedicated_handler = False
        if service == 1:
            verif_tm = Service1Tm.unpack(
                data=packet, params=UnpackParams(CdsShortTimestamp.empty(), 1, 2)
            )
            res = self.verif_wrapper.add_tm(verif_tm)
            if res is None:
                _LOGGER.info(
                    f"Received Verification TM[{tm_packet.service}, {tm_packet.subservice}] "
                    f"with Request ID {verif_tm.tc_req_id.as_u32():#08x}"
                )
                _LOGGER.warning(
                    f"No matching telecommand found for {verif_tm.tc_req_id}"
                )
            else:
                self.verif_wrapper.log_to_console(verif_tm, res)
                self.verif_wrapper.log_to_file(verif_tm, res)
            dedicated_handler = True
        if service == 5:
            event_tm = Service5Tm.unpack(packet, time_reader=CdsShortTimestamp.empty())
            self.dlogger.info(
                f"Received event packet TM [{event_tm.service}, {event_tm.subservice}]"
            )
            dedicated_handler = True
        if service == 17:
            ping_tm = Service17Tm.unpack(packet, time_reader=CdsShortTimestamp.empty())
            dedicated_handler = True
            if ping_tm.subservice == 2:
                self.dlogger.info("Received Ping Reply TM[17,2]")
            else:
                self.dlogger.info(
                    f"Received Test Packet with unknown subservice {tm_packet.subservice}"
                )
        if tm_packet is None:
            _LOGGER.info(
                f"The service {service} is not implemented in Telemetry Factory"
            )
            tm_packet = PusTelemetry.unpack(
                packet, time_reader=CdsShortTimestamp.empty()
            )
        self.raw_logger.log_tm(tm_packet)
        if not dedicated_handler and tm_packet is not None:
            pass
            # TODO: Create more generic print method..
            # self.printer.handle_long_tm_print(packet_if=tm_packet, info_if=tm_packet)


class TcHandler(TcHandlerBase):
    def __init__(
        self,
        seq_count_provider: FileSeqCountProvider,
        verif_wrapper: VerificationWrapper,
    ):
        super(TcHandler, self).__init__()
        self.seq_count_provider = seq_count_provider
        self.verif_wrapper = verif_wrapper
        self.queue_helper = DefaultPusQueueHelper(
            queue_wrapper=QueueWrapper.empty(),
            seq_cnt_provider=seq_count_provider,
            pus_verificator=self.verif_wrapper.pus_verificator,
            tc_sched_timestamp_len=7,
            default_pus_apid=EXAMPLE_PUS_APID,
        )

    def send_cb(self, send_params: SendCbParams):
        entry_helper = send_params.entry
        if entry_helper.is_tc:
            if entry_helper.entry_type == TcQueueEntryType.PUS_TC:
                pus_tc_wrapper = entry_helper.to_pus_tc_entry()
                pus_tc_wrapper.pus_tc.seq_count = (
                    self.seq_count_provider.get_and_increment()
                )
                self.verif_wrapper.add_tc(pus_tc_wrapper.pus_tc)
                raw_tc = pus_tc_wrapper.pus_tc.pack()
                _LOGGER.info(f"Sending {pus_tc_wrapper.pus_tc}")
                send_params.com_if.send(raw_tc)
        elif entry_helper.entry_type == TcQueueEntryType.LOG:
            log_entry = entry_helper.to_log_entry()
            _LOGGER.info(log_entry.log_str)

    def queue_finished_cb(self, helper: ProcedureWrapper):
        if helper.proc_type == TcProcedureType.DEFAULT:
            def_proc = helper.to_def_procedure()
            _LOGGER.info(
                f"Queue handling finished for service {def_proc.service} and "
                f"op code {def_proc.op_code}"
            )

    def feed_cb(self, helper: ProcedureWrapper, wrapper: FeedWrapper):
        self.queue_helper.queue_wrapper = wrapper.queue_wrapper
        if helper.proc_type == TcProcedureType.DEFAULT:
            def_proc = helper.to_def_procedure()
            service = def_proc.service
            if (
                service == CoreServiceList.SERVICE_17
                or service == CoreServiceList.SERVICE_17_ALT
            ):
                return self.queue_helper.add_pus_tc(
                    PusTelecommand(service=17, subservice=1)
                )


# Note about lint disable: I could split up the function but I prefer to have the whole
# running main in one block for the example.
def main():  # noqa: C901
    # Apply the library logger formatting to the own root logger. Library logs will be propagated
    # to application logger.
    add_colorlog_console_logger(_LOGGER)
    tmtccmd.init_printout(False)
    hook_obj = ExampleHookClass(json_cfg_path=default_json_path())
    parser_wrapper = PreArgsParsingWrapper()
    parser_wrapper.create_default_parent_parser()
    parser_wrapper.create_default_parser()
    parser_wrapper.add_def_proc_args()
    params = SetupParams()
    post_args_wrapper = parser_wrapper.parse(hook_obj=hook_obj, setup_params=params)
    proc_wrapper = ProcedureParamsWrapper()
    if post_args_wrapper.use_gui:
        post_args_wrapper.set_params_without_prompts(proc_wrapper)
    else:
        post_args_wrapper.set_params_with_prompts(proc_wrapper)
    params.apid = EXAMPLE_PUS_APID
    setup_args = SetupWrapper(
        hook_obj=hook_obj, setup_params=params, proc_param_wrapper=proc_wrapper
    )
    # Create console logger helper and file loggers
    tmtc_logger = RegularTmtcLogWrapper()
    printer = FsfwTmTcPrinter(tmtc_logger.logger)
    raw_logger = RawTmtcTimedLogWrapper(when=TimedLogWhen.PER_HOUR, interval=1)
    verificator = PusVerificator()
    verification_wrapper = VerificationWrapper(
        verificator, _LOGGER, printer.file_logger
    )
    # Create primary TM handler and add it to the CCSDS Packet Handler
    tm_handler = PusTmHandler(verification_wrapper, printer, raw_logger)
    ccsds_handler = CcsdsTmHandler(generic_handler=None)
    ccsds_handler.add_apid_handler(tm_handler)

    # Create TC handler
    seq_count_provider = PusFileSeqCountProvider()
    tc_handler = TcHandler(seq_count_provider, verification_wrapper)
    tmtccmd.setup(setup_args=setup_args)
    init_proc = params_to_procedure_conversion(setup_args.proc_param_wrapper)
    tmtc_backend = tmtccmd.create_default_tmtc_backend(
        setup_wrapper=setup_args,
        tm_handler=ccsds_handler,
        tc_handler=tc_handler,
        init_procedure=init_proc,
    )
    tmtccmd.start(tmtc_backend=tmtc_backend, hook_obj=hook_obj)
    try:
        while True:
            state = tmtc_backend.periodic_op(None)
            if state.request == BackendRequest.TERMINATION_NO_ERROR:
                sys.exit(0)
            elif state.request == BackendRequest.DELAY_IDLE:
                _LOGGER.info("TMTC Client in IDLE mode")
                time.sleep(3.0)
            elif state.request == BackendRequest.DELAY_LISTENER:
                time.sleep(0.8)
            elif state.request == BackendRequest.DELAY_CUSTOM:
                if state.next_delay.total_seconds() <= 0.4:
                    time.sleep(state.next_delay.total_seconds())
                else:
                    time.sleep(0.4)
            elif state.request == BackendRequest.CALL_NEXT:
                pass
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    main()
