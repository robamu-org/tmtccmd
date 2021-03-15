<p align="center"> <img src=docs/logo_tmtccmd.png width="30%"> </p>

TMTC Client Core [![Documentation Status](https://readthedocs.org/projects/tmtccmd/badge/?version=latest)](https://tmtccmd.readthedocs.io/en/latest/?badge=latest)
====

## Overview

This client was first developed by KSat for the SOURCE project to test the on-board software but
has evolved into a more generic tool for satellite developers to perform TMTC 
(Telemetry and Telecommand) handling and testing via different communication interfaces. 
Currently, only the PUS standard is implemented as a packet standard. This tool can be used either 
as a command line tool or as a GUI tool but the GUI capabilities are still in an Alpha state. 

This client currently supports the following communication interfaces:

1. Ethernet, UDP packets
2. Serial Communication 
3. QEMU

An implementation of the TCP protocol is planned.

## Documentation

The documentation will soon be moved to the `docs` folder which contains the documentation in
form of `.rst` files. These can be converted to HTML and PDF format with 
[Sphinx](https://docs.readthedocs.io/en/stable/intro/getting-started-with-sphinx.html).
An online version is available [here](https://tmtccmd.readthedocs.io/en/latest/).

## Examples 

An example which does not require additional software or hardware is still work-in-progress.

## Installation

It is recommended to use Python 3.8 and clone this repository.
After than you can still the package with `pip install .` until it has moved to PyPI. 

