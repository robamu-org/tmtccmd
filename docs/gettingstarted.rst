===============
Getting Started
===============

The example provided in the ``example`` folder of the Python package is a good place to get started.
You can run the ``tmtc_cli.py`` file to test the CLI interface or the ``tmtc_gui.py`` file
to test the GUI interface. The only working communication interface for the example applications is 
the ``dummy`` interface.

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

Implementing the hook function
==============================

Coming Soon