.. tmtccmd documentation master file, created by
   sphinx-quickstart on Sat Feb 20 23:00:59 2021.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to the TMTC Commander Core documentation!
=================================================

This module is a generic tool for satellite developers to perform TMTC (Telemetry and Telecommand)
handling and testing via different communication interfaces. Currently, only the PUS standard is
implemented as a packet standard. This tool can be used either as a command line tool
or as a GUI tool but the GUI capabilities are still in an alpha state. 
The generic parts were decoupled from the former TMTC program
to allow for easier adaption to other missions.

This client currently supports the following communication interfaces:

1. TCP/IP with UDP and TCP
2. Serial Communication using fixed frames or a simple ASCII based transport layer
3. QEMU, using a virtual serial interface

Other pages (online)

- `project page on GitHub`_
- This page, when viewed online is at https://tmtccmd.readthedocs.io/en/latest/

.. _`project page on GitHub`: https://github.com/robamu-org/tmtccmd

Contents
========

.. toctree::
   :maxdepth: 2
   
   introduction
   gettingstarted
   api

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
