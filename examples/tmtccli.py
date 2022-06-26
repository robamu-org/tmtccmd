#!/usr/bin/env python3
"""Example application for the TMTC Commander"""
import sys
import time

import tmtccmd
from tmtccmd.ccsds.handler import CcsdsTmHandler
from tmtccmd.config import default_json_path
from tmtccmd.config import ArgParserWrapper, SetupWrapper
from tmtccmd.core import BackendController, Request
from tmtccmd.logging import get_console_logger
from tmtccmd.logging.pus import (
    RegularTmtcLogWrapper,
    RawTmtcTimedLogWrapper,
    TimedLogWhen,
)

from common import TcHandler, PusHandler, ExampleHookClass, APID
from tmtccmd.utility.tmtc_printer import FsfwTmTcPrinter

LOGGER = get_console_logger()


def main():
    tmtccmd.init_printout(False)
    hook_obj = ExampleHookClass(json_cfg_path=default_json_path())
    parser_wrapper = ArgParserWrapper()
    parser_wrapper.parse(hook_obj, True)
    setup_args = SetupWrapper(
        hook_obj=hook_obj, use_gui=False, apid=APID, setup_params=parser_wrapper.params
    )
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
        setup_args=setup_args, tm_handler=ccsds_handler, tc_handler=tc_handler
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
