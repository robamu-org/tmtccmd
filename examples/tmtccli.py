#!/usr/bin/env python3
"""Example application for the TMTC Commander"""
import tmtccmd
from tmtccmd.ccsds.handler import CcsdsTmHandler, ApidTmHandlerBase
from tmtccmd.config import default_json_path
from tmtccmd.config.args import ArgParserWrapper
from tmtccmd.config import SetupArgs
from tmtccmd.logging import get_console_logger

from config.hook_implementation import ExampleHookClass
from config.definitions import APID, pre_send_cb
from config.tm_handler import default_ccsds_packet_handler

LOGGER = get_console_logger()


def main():
    print(f"-- example tmtc v{tmtccmd.__version__} --")
    tmtccmd.init_printout(False)
    hook_obj = ExampleHookClass(json_cfg_path=default_json_path())
    parser_wrapper = ArgParserWrapper()
    parser_wrapper.parse(hook_obj, True)
    setup_args = SetupArgs(
        hook_obj=hook_obj, use_gui=False, apid=APID, args_wrapper=parser_wrapper
    )
    apid_handler = ApidTmHandlerBase(
        cb=default_ccsds_packet_handler, max_queue_len=50, user_args=None
    )
    ccsds_handler = CcsdsTmHandler()
    ccsds_handler.add_apid_handler(apid=APID, handler=apid_handler)
    tmtccmd.runner.setup(setup_args=setup_args)
    tmtccmd.runner.add_ccsds_handler(ccsds_handler)
    tmtc_backend = tmtccmd.runner.create_default_tmtc_backend(
        setup_args=setup_args,
        tm_handler=ccsds_handler,
    )
    tmtc_backend.usr_send_wrapper = (pre_send_cb, None)
    tmtccmd.runner.start(tmtc_backend=tmtc_backend)


if __name__ == "__main__":
    main()
