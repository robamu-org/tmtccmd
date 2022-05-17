===============
Getting Started
===============

The example provided in the ``example`` folder of the Python package is a good place to get started.
You can run the ``tmtccli.py`` file to test the CLI interface or the ``tmtcgui.py`` file
to test the GUI interface. The only working communication interface for the example applications is 
the ``dummy`` interface.

In general, the main function will only consist of a few calls to the :py:mod:`tmtccmd` package.
The first step is to import some important modules in the :py:mod:`tmtccmd.runner` module.
The example application for the CLI mode looks like this:

::

   import tmtccmd.runner as runner
   from tmtccmd.ccsds.handler import CcsdsTmHandler, ApidHandler
   from tmtccmd.config import SetupArgs, default_json_path
   from tmtccmd.logging import get_console_logger

   from config.hook_implementation import ExampleHookClass
   from config.definitions import APID, pre_send_cb
   from config.tm_handler import default_ccsds_packet_handler

   LOGGER = get_console_logger()


   def main():
       runner.init_printout(True)
       hook_obj = ExampleHookClass(json_cfg_path=default_json_path())
       setup_args = SetupArgs(hook_obj=hook_obj, use_gui=True, apid=APID, cli_args=None)
       apid_handler = ApidHandler(
           cb=default_ccsds_packet_handler, queue_len=50, user_args=None
       )
       ccsds_handler = CcsdsTmHandler()
       ccsds_handler.add_tm_handler(apid=APID, handler=apid_handler)
       runner.setup(setup_args=setup_args)
       runner.add_ccsds_handler(ccsds_handler)
       tmtc_backend = runner.create_default_tmtc_backend(
           setup_args=setup_args,
           tm_handler=ccsds_handler,
       )
       tmtc_backend.usr_send_wrapper = (pre_send_cb, None)
       runner.run(tmtc_backend=tmtc_backend)


   if __name__ == "__main__":
       main()


1. The ``ExampleHookClass`` is located inside the
   `examples/config <https://github.com/robamu-org/tmtccmd/blob/main/examples/config/hook_implementation.py>`_ folder and contains all
   important hook implementations.
#. An argument parser is created and converted to also parse all CLI arguments required
   by ``tmtccmd``
#. A :py:class:`tmtccmd.config.SetupArgs` class is created which contains most of the
   configuration required by ``tmtccmd``. The CLI arguments are also passed to this
   class
#. An :py:class:`tmtccmd.ccsds.handler.ApidHandler` is created to handle all telemetry
   for the application APID. This handler takes a user callback to handle the packets
#. After that, a generic :py:class:`tmtccmd.ccsds.handler.CcsdsTmHandler` is
   created and the APID handler is added to it. This allows specifying different handler for
   different APIDs
#. Finally, a TMTC backend is created. A backend is required for the :py:func:`tmtccmd.runner.run`
   function.
#. A pre-send callback is added to the backend. Each time a telecommand is sent, this callback
   will be called

Most of the TMTC commander configuration is done through the hook object instance and the setup
object. More information about its implementation will be provided in the :ref:`hook-func-label`
chapter.

CLI
===

If ``tmtccli.py`` is run without any command line arguments the commander core will prompt values
like the service or operation code. These values are passed on to the hook functions, which
allows a developers to package different telecommand stacks for different service and op code
combinations.

GUI
===

Simply run the ``tmtcgui.py`` application and connect to the Dummy communication interface.
After that, you can send a ping command and see the generated replies.

.. _hook-func-label:
 
Implementing the hook function
==============================

Coming Soon
