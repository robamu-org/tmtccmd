=============
 Introduction
=============

Overview
=========

This commander was written for the `SOURCE`_ project as a way to simplify the
software testing. The goal was to make it as easy as possible to send telecommands (TCs)
to the On-Board Software (OBSW) running on an external On-Board Computer (OBC) and to analyse
the telemetry (TMs) coming back. The following graph shows two possible ways to use
the TMTC commander

.. image:: images/tmtccmd_usage.PNG
	:align: center
	
The first way assumes that the OBSW can be run on a host computer and starts a TPC/IP
server internally. The TMTC commander can then be used to send telecommands via the TCP/IP
interface. The second way assumes that the OBSW is run on an external microcontroller.
Here, the serial interface is used to send telecommands. Other ways like sending TMTCs 
via Ethernet to a microcontroller running a TCP/IP server are possible as well.

.. _`SOURCE`: https://www.ksat-stuttgart.de/en/our-missions/source/

The application is configured by passing an instance of a special hook object to the commander core
using the ``initialize_tmtc_commander`` function and then running the ``run_tmtc_commander``
function which also allows to specify whether the CLI or the GUI functionality is used. It is
recommended to implement the class ``TmTcHookBase`` for the hook object instantiation
because this class contains all important functions as abstract functions.

Features
=========

- `Packet Utilisation Standard (PUS)`_ TMTC stack to simplify the packaging of PUS telecommand
  packets and the analysis and deserialization of raw PUS telemetry
- Common communication interfaces like a serial interface or a TCP/IP interfaces
  to send and receive TMTC packets.
- Listener mode to display incoming packets
- Sequential mode which allows inserting telecommands into a queue
  and sending them in a sequential way, allowing to analyse the telemetry 
  generated for each telecommand separately
- Special internal queue commands which allow operations like informative printouts or send delays
- Components to simplify the handling of housekeeping replies (PUS Service 8) or action command 
  replies (PUS Service 3)
- Components to automatically deserialize telecommand verification replies (PUS Service 1)
  or Event replies (PUS Service 5)

.. _`Packet Utilisation Standard (PUS)`: https://ecss.nl/standard/ecss-e-st-70-41c-space-engineering-telemetry-and-telecommand-packet-utilization-15-april-2016/

