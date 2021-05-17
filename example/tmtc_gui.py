#!/usr/bin/env python3
"""
Example application for the TMTC Commander
"""
from tmtccmd.runner import run_tmtc_commander, initialize_tmtc_commander
from config.hook_implementation import ExampleHookClass


def main():
    hook_obj = ExampleHookClass()
    initialize_tmtc_commander(hook_object=hook_obj)
    run_tmtc_commander(use_gui=True, app_name="TMTC Commander Example")


if __name__ == '__main__':
    main()

