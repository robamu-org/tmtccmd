#!/usr/bin/env python3
"""Example application for the TMTC Commander
"""
from tmtccmd.ccsds.handler import CcsdsTmHandler, ApidHandler
import tmtccmd.runner as tmtccmd
from tmtccmd.config import SetupArgs, default_json_path
from tmtccmd.config.args import (
    create_default_args_parser,
    add_default_tmtccmd_args,
    parse_default_input_arguments,
)
from tmtccmd.tm.handler import default_ccsds_packet_handler

from config.hook_implementation import ExampleHookClass
from config.definitions import APID


def main():
    tmtccmd.init_printout(False)
    hook_obj = ExampleHookClass(json_cfg_path=default_json_path())
    arg_parser = create_default_args_parser()
    add_default_tmtccmd_args(arg_parser)
    args = parse_default_input_arguments(arg_parser, hook_obj)
    setup_args = SetupArgs(hook_obj=hook_obj, use_gui=False, cli_args=args)
    apid_handler = ApidHandler(
        cb=default_ccsds_packet_handler, queue_len=50, user_args=None
    )
    ccsds_handler = CcsdsTmHandler()
    ccsds_handler.add_tm_handler(apid=APID, handler=apid_handler)
    tmtccmd.setup(setup_args=setup_args)
    tmtc_backend = tmtccmd.get_default_tmtc_backend(
        setup_args=setup_args,
        tm_handler=ccsds_handler,
    )
    tmtccmd.add_ccsds_handler(ccsds_handler)
    tmtccmd.run(tmtc_backend=tmtc_backend)


if __name__ == "__main__":
    main()
