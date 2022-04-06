#!/usr/bin/env python3
"""Example application for the TMTC Commander"""
import tmtccmd.runner
from tmtccmd.ccsds.handler import CcsdsTmHandler, ApidHandler
from tmtccmd.config import SetupArgs, default_json_path
from tmtccmd.logging import get_console_logger

from config.hook_implementation import ExampleHookClass
from config.definitions import APID, pre_send_cb
from config.tm_handler import default_ccsds_packet_handler

LOGGER = get_console_logger()


def main():
    tmtccmd.runner.init_printout(True)
    hook_obj = ExampleHookClass(json_cfg_path=default_json_path())
    setup_args = SetupArgs(hook_obj=hook_obj, use_gui=True, apid=APID, cli_args=None)
    apid_handler = ApidHandler(
        cb=default_ccsds_packet_handler, queue_len=50, user_args=None
    )
    ccsds_handler = CcsdsTmHandler()
    ccsds_handler.add_tm_handler(apid=APID, handler=apid_handler)
    tmtccmd.runner.setup(setup_args=setup_args)
    tmtccmd.runner.add_ccsds_handler(ccsds_handler)
    tmtc_backend = tmtccmd.runner.create_default_tmtc_backend(
        setup_args=setup_args,
        tm_handler=ccsds_handler,
    )
    tmtc_backend.usr_send_wrapper = (pre_send_cb, None)
    tmtccmd.runner.run(tmtc_backend=tmtc_backend)


if __name__ == "__main__":
    main()
