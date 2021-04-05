=============
 Introduction
=============

Overview
=========

This commander was written for the `SOURCE` project as a way to simplify the
software testing. The goal was to make it as easy as possible to send telecommands (TCs)
to the On-Board Software running on an external On-Board Computer and to analyse
the telemetry (TMs) coming back. The following graph shows two possible ways to use
the TMTC commander

.. image:: images/tmtccmd_usage.pdf
	:align: center
	
.. SOURCE: https://www.ksat-stuttgart.de/en/our-missions/source/

Features
=========

- `Packet Utilisation Standard (PUS)` TMTC stack to simplify the packaging of PUS telecommand 
  packets and the analysis and deserialization of raw PUS telemetry
- Common communicaiton interfaces like a serial interface or a TCP/IP interface
  to send and receive TMTC packets.
- Listener mode to display incoming packets
- Sequential mode which allows inserting telecommands into a queue
  and sending them in a sequential way, allowing to analyse the telemetry 
  generated for each telecommand

.. Packet Utilisation Standard (PUS): https://ecss.nl/standard/ecss-e-st-70-41c-space-engineering-telemetry-and-telecommand-packet-utilization-15-april-2016/

