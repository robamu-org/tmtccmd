#!/usr/bin/env python3
"""
Example application for the TMTC Commander
"""
from tmtccmd.ccsds.handler import CcsdsTmHandler, ApidHandler
import tmtccmd.runner as tmtccmd
from tmtccmd.config import SetupArgs, default_json_path
from tmtccmd.logging import get_console_logger
from tmtccmd.tm.handler import default_ccsds_packet_handler

from config.hook_implementation import ExampleHookClass
from config.definitions import APID, pre_send_cb


LOGGER = get_console_logger()


def main():
    tmtccmd.init_printout(True)
    hook_obj = ExampleHookClass(json_cfg_path=default_json_path())
    setup_args = SetupArgs(hook_obj=hook_obj, use_gui=True, apid=APID, cli_args=None)
    apid_handler = ApidHandler(
        cb=default_ccsds_packet_handler, queue_len=50, user_args=None
    )
    ccsds_handler = CcsdsTmHandler()
    ccsds_handler.add_tm_handler(apid=APID, handler=apid_handler)
    tmtccmd.setup(setup_args=setup_args)
    tmtccmd.add_ccsds_handler(ccsds_handler)
    tmtc_backend = tmtccmd.get_default_tmtc_backend(
        setup_args=setup_args,
        tm_handler=ccsds_handler,
    )
    tmtc_backend.set_pre_send_cb(callable=pre_send_cb, user_args=None)
    tmtccmd.run(tmtc_backend=tmtc_backend)


if __name__ == "__main__":
    main()
