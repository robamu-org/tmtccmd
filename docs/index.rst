.. tmtccmd documentation master file, created by
   sphinx-quickstart on Sat Feb 20 23:00:59 2021.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

TMTC Commander Documentation
=============================

This commander application was first developed for the
`SOURCE <https://www.ksat-stuttgart.de/en/our-missions/source/>`_ project to test the on-board
software but has evolved into a small Python framework for satellite developers to perform TMTC
(Telemetry and Telecommand) handling and testing via different communication interfaces.
This tool can be used either as a command line tool or as a GUI tool. The GUI features require a
PyQt5 installation. This package also has dedicated support to send and receive ECSS PUS packets
or other generic CCSDS packets.

This client currently supports the following communication interfaces:

1. TCP/IP with UDP and TCP
2. Serial Communication using fixed frames or a simple ASCII based transport layer
3. QEMU, using a virtual serial interface

The TMTC commander also includes some telemetry handling components and telecommand packaging
helpers. Some of those components are tailored towards usage with the
`Flight Software Framework (FSFW) <https://egit.irs.uni-stuttgart.de/fsfw/fsfw/>`_.

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
