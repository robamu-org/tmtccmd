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
the :py:class:`tmtccmd.config.hook.HookBase`.

1. The :py:meth:`tmtccmd.config.hook.HookBase.assign_communication_interface` method
   is used to return a communication interface given a string identifier. You can read more
   about the communication abstraction in the :ref:`com` chapter.
2. The :py:meth:`tmtccmd.config.hook.HookBase.get_tmtc_definitions` returns a configuration
   wrapper which determines the commands displayed when using the interactive CLI mode or the GUI.

The TC handler
---------------

This object is responsible for the telecommand handling. Therefore this object implements
the :py:class:`tmtccmd.tc.handler.TcHandlerBase`.

In the example case, the handler object is reponsible for returning telecommand queues based on
input information. This task is done by the :py:meth:`tmtccmd.tc.handler.TcHandlerBase.feed_cb`
callback method.

The actual handling of telecommand queue entries is done in the
:py:meth:`tmtccmd.tc.handler.TcHandlerBase.send_cb` method implementation. One thing to note here
is that a queue entry does not necessarily have to be a command to be sent. For example,
the queue can also contain something like log requests or delay requests, or even complete
custom requests. These requests can then be handled by the user.

The PUS TM handler
--------------------

This object is responsible for the handling of PUS telemetry. In the example case, the
handler object is responsible space packets with a certain application process identifier (APID).
Therefore, this object implements the :py:class:`tmtccmd.tm.SpecificApidHandlerBase`.

The `handle_tm` method implementation is the primary functions where incoming PUS packets
are handled. This can something like prinouts or logging, either to a file or to a database.

Other example applications
===========================
The `EIVE <https://egit.irs.uni-stuttgart.de/eive/eive-tmtc>`_ and
`SOURCE <https://git.ksat-stuttgart.de/source/tmtc>`_ project implementation of the TMTC commander
provide more complex implementations.

..
    TODO: More explanations for example
