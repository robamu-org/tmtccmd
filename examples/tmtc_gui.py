#!/usr/bin/env python3
"""
Example application for the TMTC Commander
"""
from tmtccmd.ccsds.handler import CcsdsTmHandler, ApidHandler
import tmtccmd.runner as tmtccmd
from tmtccmd.tm.handler import default_ccsds_packet_handler

from config.hook_implementation import ExampleHookClass
from config.definitions import APID


def main():
    hook_obj = ExampleHookClass()
    tmtccmd.init_tmtccmd(hook_object=hook_obj)
    apid_handler = ApidHandler(
        cb=default_ccsds_packet_handler, queue_len=50, user_args=None
    )
    ccsds_handler = CcsdsTmHandler()
    ccsds_handler.add_tm_handler(apid=APID, handler=apid_handler)
    tmtccmd.setup_tmtccmd(use_gui=True, reduced_printout=False)
    tmtc_backend = tmtccmd.get_default_tmtc_backend(
        hook_obj=hook_obj,
        json_cfg_path=hook_obj.get_json_config_file_path(),
        tm_handler=ccsds_handler,
    )
    tmtccmd.add_ccsds_handler(ccsds_handler)
    tmtccmd.run_tmtccmd(use_gui=True, tmtc_backend=tmtc_backend)


if __name__ == "__main__":
    main()
