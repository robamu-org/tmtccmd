<p align="center"> <img src="docs/logo_tmtccmd_smaller.png" width="40%"> </p>

TMTC Commander Core [![Documentation Status](https://readthedocs.org/projects/tmtccmd/badge/?version=latest)](https://tmtccmd.readthedocs.io/en/latest/?badge=latest)
[![pytest](https://github.com/rmspacefish/tmtccmd/actions/workflows/ci.yml/badge.svg?branch=develop&event=push)](https://github.com/rmspacefish/tmtccmd/actions/workflows/ci.yml)
====

## Overview

- Documentation: https://tmtccmd.readthedocs.io/en/latest/
- Project Homepage: https://github.com/rmspacefish/tmtccmd

This commander application was first developed by KSat for the 
[SOURCE](https://www.ksat-stuttgart.de/en/our-missions/source/) project to test the on-board 
software but has evolved into a more generic tool for satellite developers to perform TMTC 
(Telemetry and Telecommand) handling and testing via different communication interfaces. 
Currently, only the PUS standard is implemented as a packet standard. This tool can be used either 
as a command line tool or as a GUI tool, but the GUI capabilities are still in an alpha state.

This client currently supports the following communication interfaces:

1. TCP/IP with UDP packets
2. Serial Communication using fixed frames or a simple ASCII based transport layer
3. QEMU, using a virtual serial interface

A TCP implementation is planned.

The TMTC commander also includes a Space Packet and a ECSS PUS packet stack. Some of these
components might be moved to an own library soon, so they were decoupled from the rest 
of the TMTC commander components.

## Examples 

An example which does not require additional software or hardware is still work-in-progress.
Until then, the [SOURCE](https://git.ksat-stuttgart.de/source/tmtc) implementation provides
a good starting point to get started.

## Tests

The tests are still work-in-progress. The first tests will target the internal
PUS TMTC packaging modules.

## Installation

On Ubuntu, if `pip` is not installed yet, you can install it with

```sh
sudo apt-get install python3-pip
```

It is recommended to use Python 3.8.
For developers, it is recommended to add this repostiory as a submodule
with the following command:

```sh
git submodule add https://github.com/rmspacefish/tmtccmd.git
```

For the following commands, replace `python3` with `py` on Windows.
After that, you can install the package in an editable mode with the following command:

```sh
cd tmtccmd
python3 -m pip install -e .
```

To also install the requirements for the GUI mode, run this command instead

```sh
cd tmtccmd
python3 -m pip install -e .[gui]
```

Omit the `-e` for a regular installation. The package might move to PyPI soon.
After that, installation will also be possible with `pip install tmtccmd`
and `pip install tmtccmd[gui]`.
