===============
Getting Started
===============

Example Project
================

The `example application <https://github.com/robamu-org/tmtccmd/tree/main/examples>`_ is the best
way to learn how this framework use and to get started. It shows how to set up handles
classes for TC and TM handling and then ties together all components.

Some explanation of classes and modules inside the example are given here.

The example hook class
______________________

The class `ExampleHookClass` is the example configuration class implementing
the :py:class:`tmtccmd.config.hook.TmTcCfgHookBase`.

1. The :py:meth:`tmtccmd.config.hook.TmTcCfgHookBase.assign_communication_interface` method
   is used to return a communication interface given a string identifier.
2. The :py:meth:`tmtccmd.config.hook.TmTcCfgHookBase.get_tmtc_definitions` returns a configuration
   wrapper which determines the commands displayed when using the interactive CLI mode or the GUI.

The TC handler
---------------

This object is responsible for the telecommand handling.

The PUS TM handler
-----------------

This object is responsible for the handling of PUS telemetry.

Other example applications
===========================
The `EIVE <https://egit.irs.uni-stuttgart.de/eive/eive-tmtc>`_ and
`SOURCE <https://git.ksat-stuttgart.de/source/tmtc>`_ project implementation of the TMTC commander
provide more complex implementations.

..
    TODO: More explanations for example
