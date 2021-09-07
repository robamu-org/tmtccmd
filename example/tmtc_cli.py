#!/usr/bin/env python3
"""Example application for the TMTC Commander
"""
from tmtccmd.ccsds.handler import CcsdsTmHandler
from tmtccmd.runner import run_tmtc_commander, initialize_tmtc_commander, add_ccsds_handler
from tmtccmd.tm.handler import default_ccsds_packet_handler

from config.hook_implementation import ExampleHookClass
from config.definitions import APID


def main():
    hook_obj = ExampleHookClass()
    initialize_tmtc_commander(hook_object=hook_obj)
    ccsds_handler = CcsdsTmHandler()
    ccsds_handler.add_tm_handler(
        apid=APID, pus_tm_handler=default_ccsds_packet_handler, max_queue_len=50
    )
    add_ccsds_handler(ccsds_handler)
    run_tmtc_commander(use_gui=False)


if __name__ == '__main__':
    main()
