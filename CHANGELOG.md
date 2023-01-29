Change Log
=======

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/).

# [unreleased]

## Added

- `tmtccmd.pus.pus_20_fsfw_params_defs`: New `ParameterId` and `Parameter` helper
  dataclasses. Also added `Service20ParamDumpWrapper` helper class
  to help with the deserialization of parameters. The helper classes can be used both
  for TC and TM handling. Create new API set to create the `Parameter` classes for common
  parameter types.

## Changed

- `tmtccmd.tc.pus_20_params.py`: Create new `crate_fsfw_load_param_cmd` and
  deprecate the former `pack_fsfw_load_param_cmd` function.
- (breaking): Renamed `tmtccmd.tc.pus_20_params.py` to
  `tmtccmd.tc.pus_20_fsfw_params.py` to reflect these modules are tailored
  towards usage with the FSFW.
- (breaking): Reworked `tmtccmd.tm.pus_20_fsfw_params` by simplifying `Service20FsfwTm`
  significantly. It only implements `AbstractPusTm` now and is a simple wrapper
  around `PusTelemetry`, which is exposed as a `pus_tm` member.
- (breaking): Renamed `tm.pus_5_event` to `tm.pus_5_fsfw_event` to better reflect these modules
  are tailored towards usage with the FSFW
- (breaking): Simplified `Service5Tm significantly`. It only implements `AbstractPusTm` now and
  is a more simple wrapper around `PusTelemetry` exposing some FSFW specific functionality.

# [v4.0.0a2] 2023-01-23

## Added

- Added `apid` and `seq_count` optional arguments back to generic
  (not FSFW specific) TC constructors.
- Cleaned up telecommand and telemetry code, removed a lot of obsolete
  functionality

## Changed

- (breaking) `pus` module: Renamed `pus_?...` modules to `s?_...`. These modules
  now re-export all their definitions and everything in their similarly
  named `tm` and `tc` modules.
- (breaking) `pus.pus_8_funccmd`: Renamed `Subservices` to `CustomSubservice`
- TC creation API: Replace `generate_...` API with `create_...` API for consistency
- (breaking) Renamed `Subservices` to `Subservice`, use singular enum because they are not
  flag enums.
- (breaking) `pus_200_fsfw_modes`: Rename `Modes` to `Mode`.
- Subservice enumerations: Add missing `TM_...` and `TC_...` prefixes where applicable
- Use concrete `spacepackets` version 0.14.0rc1

# [v4.0.0a1] 2023-01-12

## Fixed

- `enable_periodic_hk_command`: Remove third obsolete ssc argument

# [v4.0.0a0] 2023-01-05

## Added

- New `SerialCobsComIF` communication interface to send and received COBS encoded packets.

## Changes

- `CoreComInterfaces`: Renamed `ser_*` interface names to `serial_*`.
- Split up the `SerialComIF` into distinct classes:
  - `SerialFixedFrameComIF`, but this one has also been deprecated now.
  - `SerialDleComIF` for sending and receiving DLE encoded packets.
- Switched to compatible release requirement for dependencies.
- `ComInterface`: Added new abstract method `get_id`, removed `__init__` dunder.

# [v3.0.1] 2023-01-05

## Changes

- Marked `Service17TmExtended` as deprecated.

## Fixes

- Minor fixes for GUI: Moved communication interface switching to
  separate worker thread.

# [v3.0.0] 2022-12-09

- Minor cleaning up
- Added some FSFW specific functionality to retrieve validity lists from a bitfield representation

# [v3.0.0rc3] 2022-12-01

- Some bugfixes for GUI, improved teardown/close handling

# [v3.0.0rc2] 2022-11-20

- Add `deprecation` dependency to allow marking functions and classes
  as deprecated with a decorator
- Improve test structure
- Improve documentation
- Add decorators `service_provider` and `tmtc_definitions_provider` which
  avoids some boilerplate code when registering definition provider or packet creation
  handlers

# [v3.0.0rc1] 2022-07-03

- Overhaul of application architecture
- Significant simplification of various modules to increase testability
- Test coverage increased
- Reduced number of modules significantly by moving code into the repective `__init__` files where
  possible
- GUI improved, added separate TM listening button
- Documentation improved
- New logo
- Simplified general package structure, remove `src` folder and have `tmtccmd` package and `tests`
  package in repo root
- First CFDP handler components
- Reduce usage of globals. The end goal is to remove them altogether
- Reduce overall number of spawned threads
- Added Sequence Count handling modules

# [v2.2.2]

- Improve internal structure of sequential sender receiver object
- Add some PUS11 Telecommand Scheduling helpers
- Bugfixes for new modules and code

# [v2.2.1]

- Minor fix for CI/CD

# [v2.2.0]

- Improve `lint.py`: Add prefix and print out executed command
- Architectural improvements for the `TmListener` component
  - Separate functions to set the internal mode
  - Moved mode enum outside of class scope
- Call user send callback for both queue commands and regular telecommands

## TmTcHandler

- Added a cached `SequentialCommandSenderReceiver`
- Added `CONTINUOUS` mode which will start the receiver thread in the 
  `SequentialCommandSenderReceiver` instance and only send one TC

## Runner module

- Added argument in `__start_tmtc_commander_cli` to defer sending of command
- Added two functions, `init_and_start_daemons` and `performOperation`, to allow
  separate calls to initiate the TmTcHandler and send TCs

## SequentialCommandSenderReceiver

- Added `send_queue_tc_and_return` function which does only that (and no TM checking)
- Added possibility to start a thread which checks TM

## [v2.1.0]

- API consolidation for PUS TCs and TMs. Unified the API and made it more consistent

## [v2.0.1]

### Fixed

- Bugs in examples

## [v2.0.0]

### Changed

- Improve core API: Changes core functions to setup and run. Requirement to user to create backend.
  Makes it easier to directly configure the backend and move to a generally more pythonic API
- Refactoring and extending file logging functionalities
- Exposes functions to create a raw PUS logger and a TMTC logger
- Refactor modules to move packet printout and logging to user level
- Simplified hook object, removed 2 static PUS handlers
- Updated CCSDS Handler to make it more easily extensible by creating a new ApidHandler class
- New Pre-Send Callback which is called by backend before sending each telecommand

### Added

- Parsing functions to parse the CSV files generated by the FSFW generators.
  Includes event, object ID and returnvalue files. These parsing functions
  generate dictionaries.
- New function in Hook base to return return value dictionary

## [v1.13.1]

### Fixed

- Return the config dictionary for op codes

## [v1.13.0]

### Added

- New dependency `prompt-toolkit`
- Auto-Complete feature for service and op-code selection using the `prompt-toolkit`
  packaged

### Fixed

- Added missing super constructor call for HkReplyUnpacked
- Extended Op Code options functionality and actually use it. Allows to set custom timeout
  or and enter listener mode for certain op codes

## [v1.12.0]

### API Changes

- Renamed some TM packets to make it more explicit that these TM handlers are tailored
  towards usage with the Flight Software Framework (FSFW)

### Added

- Better handling for scalar parameter telemetry for service 20. Emit better warnings for
  unimplemented cases

### Others

- Bumped some package requirements.
  - `colorlog` >= 6.6.0
  - `spacepackets` >= 0.6
  - `pyserial` >= 3.5
- Renamed example folder

### Fixes

- GUI example fixed

## [v1.11.0]

### API Changes

- Improved API to specify handling for Service 3 and Service 8 packets in user hook object

## [v1.10.2]

- New API to build service/opcode dictionary
- Fixes for Service 8 Telemetry Parser

## [v1.10.1]

- Applied consistent formatting with `black` tool
- Some bugfixes for PUS packet stack
