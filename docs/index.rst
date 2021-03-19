.. tmtccmd documentation master file, created by
   sphinx-quickstart on Sat Feb 20 23:00:59 2021.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to the TMTC Commander Core documentation!
=================================================

This module is a generic tool for satellite developers to perform TMTC (Telemetry and Telecommand)
handling and testing via different communication interfaces. Currently, only the PUS standard is
implemented as a packet standard. This tool can be used either as a command line tool
or as a GUI tool. The generic parts were decoupled from the former TMTC program and integrated into
a separate submodule to allow for easier adaption to other missions.

This client currently supports the following communication interfaces:

1. Ethernet, UDP packets
2. Serial Communication 
3. QEMU, using a virtual serial interface

The core is configured by passing a special instance of a hook object to the commander 
before calling the main ``run_tmtc_commander`` function. This hook object is implemented by the user 
and should implement the ``TmTcHookBase`` base class.

.. toctree::
   :maxdepth: 2
   :caption: Contents:

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
