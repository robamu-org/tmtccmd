===============
Getting Started
===============

The example provided in the ``example`` folder of the Python package is a good place to get started.
You can run the ``tmtc_cli.py`` file to test the CLI interface or the ``tmtc_gui.py`` file
to test the GUI interface. The only working communication interface for the example applications is 
the ``dummy`` interface.

In general, the main function will only consist of a few calls to the :py:mod:`tmtccmd` package.
The first step is to import some important modules in the :py:mod:`tmtccmd.runner` module.
The example application for the CLI mode looks like this:

::

    from tmtccmd.ccsds.handler import CcsdsTmHandler
    from tmtccmd.runner import run_tmtc_commander, initialize_tmtc_commander, add_ccsds_handler
    from tmtccmd.tm.handler import default_ccsds_packet_handler

    from config.hook_implementation import ExampleHookClass
    from config.definitions import APID


    def main():
        hook_obj = ExampleHookClass()
        initialize_tmtc_commander(hook_object=hook_obj)
        ccsds_handler = CcsdsTmHandler()
        ccsds_handler.add_tm_handler(apid=APID, pus_tm_handler=default_ccsds_packet_handler, max_queue_len=50)
        add_ccsds_handler(ccsds_handler)
        run_tmtc_commander(use_gui=False)

1. The ``ExampleHookClass`` is located inside the ``example/config`` folder and contains all
   important hook implementations.
#. The hook instance is passed to the :py:meth:`tmtccmd.runner.initialize_tmtc_commander` method
   which takes care of internal initialization.
#. After that, a generic :py:class:`tmtccmd.ccsds.handler.CcsdsTmHandler` is
   created, which can be used to handle PUS packets, which are a specific type of CCSDS packets.
   Here, it is assumed the so called Application Process Identifier or APID will be constant
   for all PUS packets.
#. A telemetry handler is added to the CCSDS handler for handling PUS telemetry with that specific
   APID.
#. The CCSDS Handler is added so it can be used by the TMTC commander core
#. Finally, the application can be started with the :py:meth:`tmtccmd.runner.run_tmtc_commander`
   call.

Most of the TMTC commander configuration is done through the hook object instance. More information
about its implementation will be provided in the :ref:`hook-func-label` chapter

CLI
===

If ``tmtc_cli.py`` is run without any command line arguments the commander core will prompt values
like the service or operation code. These values are passed on to the hook functions, which
allows a developers to package different telecommand stacks for different service and op code
combinations.

GUI
===

Simply run the ``tmtc_gui.py`` application and connect to the Dummy communication interface.
After that, you can send a ping command and see the generated replies.

.. _hook-func-label:
 
Implementing the hook function
==============================

Coming Soon
