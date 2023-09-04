Change Log
=======

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/).

Starting from v4.0.0, this project adheres to [Semantic Versioning](http://semver.org/).

# [unreleased]

# [v6.0.0rc0] 2023-09-04

- Bumped `spacepackets` to v0.18.0rc1

## Added

- The `CfdpParams` config wrapper now has an additional `proxy_op` field.
- New `cfdp_req_to_put_req_regular` and `cfdp_req_to_put_req_proxy_get_req` API to convert standard
  `CfdpParams` instances to `PutRequest`s
- The CFPD source handler is now able to convert PutRequest metadata fields to options. It is also
  able to request metadata only PDUs now, allowing it to perform proxy operations.

## Changed

- Adapted the FSFW specific Housekeeping service API to make HK requests diagnostic agnostic.
  The PUS interface has proven to be cumbersome and problematic, so the split between diagnostic
  and regular HK packets has been removed in newer version of the FSFW. The new API reflects that.
  The old API is still available by using the `*_with_diag` suffix.
- The former `PutRequestCfg` dataclass is now named `PutRequest`. The former `PutRequest` class
  is now named `PutRequestCfgWrapper` and simply wraps a `CfdpParams` dataclass.
- The CFDP source handler expects the `PutRequest` dataclass instead of a CFDP request wrapper now
  for the `put_request` API.

## Removed

- The CFDP source handler `start_cfdp_transaction` API was removed. It was only able to process
  put requests in its current form anyway. The `put_request` method is sufficient for now.
- Package version is single-sourced using the `importlib.metadata` variant: The `pyproject.toml`
  now contains the version information, but the informatio can be retrieved at runtime
  by using the new `version.get_version` API or `importlib.metadata.version("spacepackets")`.
- `setup.py` which is not required anymore.

# [v5.0.0] 2023-07-13

## Changed

- `add_def_proc_and_cfdp_as_subparsers` returns the subparsers now.

# [v5.0.0rc0] 2023-06-09

`spacepackets` version: v0.17.0

## Changed

- Moved `tmtccmd.util.tmtc_printer` module to `tmtccmd.fsfw.tmtc_printer`. Old module references
  new module, old module marked deprecated.
- The `FsfwTmtcPrinter` `get_validity_buffer` function is a `staticmethod` now.

## Fixed

- Bump of `spacepackets`: Bugfix in spacepacket parser which lead to broken packets in the TCP
  communication interface.

# [v5.0.0a0] 2023-05-14

`spacepackets` version: v0.16.0

## Fixed

- Bumped `spacepackets` to v0.16.0 for important bugfix in PDU header format.

## Added

- Added FSFW parameter service API to dump parameters.
- Added FSFW parameter service `FsfwParamId` class to uniquely identify a parameter in a
  FSFW context.

## Changed

- The FSFW parameter service helper class `Parameter` is now a composition of the raw parameter data
  and the new `FsfwParamId` class.
- The `create_load_param_cmd` API now expects a `Paramter` instead of raw data.

# [v4.1.3] 2023-06-19

## Fixed

- Dependency specifier for `spacepackets`, dependency specifier for pre v1.0 versions in general.

# [v4.1.2] 2023-03-18

## Fixed

- `logging` usage for GUI.

# [v4.1.1] 2023-02-23

## Changed

- Improvements for documentation: Added `spacepackets` cross-references.

# [v4.1.0] 2023-02-23

## Added

- Added various parameter helpers in the `pus.s20_fsfw_param` module. This includes
  helper methods to pack signed values (i8, i16 and i32), float/double vectors and matrices
  parameters.

# [v4.0.0] 2023-02-17

Starting from this version, the project will adhere to [Semantic Versioning](https:://semver.org/).
spacepackets version: v0.15.0

## Changed

- Renamed `pus.s5_event` and `pus.s5_event_defs` to `pus.s5_fsfw_event` and
  `pus.s5_fsfw_event_defs` to better reflect this module is FSFW specific.

## Added

- First sat-rs support modules: `pus.s5_satrs_event` and `pus.s5_satrs_event_defs`

## Removed

- `pack_generic_service_5_test_into` removed, not generic enough.

# [v4.0.0rc2] 2023-02-12

## Fixed

- Use custom package discovery in `pyproject.toml` similarly how to discovery
  was handled in `setup.cfg`. Auto-Discovery was problematic, package is not discovered
  correctly.

# [v4.0.0rc1] 2023-02-10

`spacepackets` version 0.14.0

## Fixed

- `config.args`: Assigning of the COM interface in the args to setup converters is now done in
  the `args_to_params_generic` function. Otherwise, this feature does not work for the conversion
  of CFDP arguments. 

## Changed

- Remove `setup.cfg` and move to `pyproject.toml`. Create new `.flake8` file accordingly.

## Added

- `tc.pus_200_fsfw_mode.create_announce_mode_command` added.

# [v4.0.0rc0] 2023-02-03

- `spacepackets` version 0.14.0rc3

## Changed

### Logging

The usage of the `logging` library now is a lot more pythonic and more
aligned to the recommended way to use the logger. The `get_console_logger` has become deprecated.
Users are encouraged to create custom application loggers using `logging.getLogger(__name__)`.
It is also possible to apply the library log format to an application logger using
`tmtccmd.logging.add_colorlog_console_logger`. 

- Mark `get_console_logger` as deprecated.
- New `tmtccmd.init_logger` method to set up library logger.
- The logging default init function does not set up an error file logger anymore.
- (breaking) Rename `set_up_colorlog_logger` to `add_colorlog_console_logger`.

## Added

- New `add_error_file_logger` function.

# [v4.0.0a3] 2023-01-31

- `spacepackets` version 0.14.0rc2

## Added

- `tmtccmd.com.ComInterface`: Added two new generic exceptions:
  - `ReceptionDecodeError` for generic decoder errors on packet reception.
  - `SendError` for generic send errors when sending packets.
- `tmtccmd.pus.pus_20_fsfw_params_defs`: New `ParameterId` and `Parameter` helper
  dataclasses. Also added `Service20ParamDumpWrapper` helper class
  to help with the deserialization of parameters. The helper classes can be used both
  for TC and TM handling. Create new API set to create the `Parameter` classes for common
  parameter types.
- `SetupParams` can now already include a COM interface instance.
- CLI arguments: Added the `--pp` or `--prompt-proc` argument which only has meaning when used
  together with the listener flag (`-l`). It should cause the main application to prompt for
  a procedure (but still go to listener mode after the procedure).

## Changed

### Argument parsing and Core modules

- (breaking): `tmtccmd.config.hook.TmTcCfgHookBase` renamed to `tmtccmd.config.hook.HookBase`.
- (breaking): The `PostArgsParsingWrapper` constructor now expects a `SetupParams` parameter and
  caches it.
  All `set_*` methods now do not expect the `SetupParams` to be passed explicitely anymore.
- (breaking): The `PreArgsParsingWrapper` now expects a `setup_params` parameter to be passed to the
  `parse` method. The parameter helper will be cached in the created `PostArgsParsingWrapper`. 
- `args_to_params_tmtc` now expects an `assign_com_if` method and can assign a COM interface
  when it is passed. It oftentimes makes sense to determine a valid COM interface
  (and prompt applicable parameters from the user) before prompting procedure parameters.
  The new behaviour is the default when using the `PostArgsParsingWrapper`.

### PUS modules

- (breaking): Renamed `tmtccmd.*.*20_params.py` to
  `tmtccmd.*.*20_fsfw_param.py` to reflect these modules are tailored
  towards usage with the FSFW.
- (breaking): Reworked `tmtccmd.tm.pus_20_fsfw_params` by simplifying `Service20FsfwTm`
  significantly. It only implements `AbstractPusTm` now and is a simple wrapper
  around `PusTelemetry`, which is exposed as a `pus_tm` member.
- (breaking): Renamed `tm.pus_5_event` to `tm.pus_5_fsfw_event` to better reflect these modules
  are tailored towards usage with the FSFW
- (breaking): Simplified `Service5Tm` significantly. It only implements `AbstractPusTm` now and
  is a more simple wrapper around `PusTelemetry` exposing some FSFW specific functionality.
- (breaking): Renamed `tmtccmd.*.*200_fsfw_modes` to `tmtccmd.*.*200_fsfw_mode` and
  `tmtccmd.*.*20_fsfw_params` to `tmtccmd.*.*20_fsfw_param` for consistency.
- `tmtccmd.tc.pus_20_params.py`: Create new `crate_fsfw_load_param_cmd` and
  deprecate the former `pack_fsfw_load_param_cmd` function.

### Other

- (breaking): `DefaultPusQueueHelper`: `seq_cnt_provider`, `pus_verificator`
  and `default_pus_apid` (formerly `pus_apid`) do not have default values anymore
  and need to be specified explicitely. 
- (breaking): Renamed `tmtccmd.config.com.ComIfCfgBase` to `ComCfgBase`
- (breaking): `tmtccmd.com.ComInterface`: Change `get_id` to `id` property.
- (breaking): TCP (`tmtccmd.com.TcpSpacePacketsComIF`) and `tmtccmd.com.UdpComIF`:
   Remove `max_recv_size` argument and replace it with 4096 where it was used.
- (breaking): TCP: Renamed `tmtccmd.com.TcpComIF` to `tmtccmd.com.TcpSpacePacketsComIF` to better
  reflect this interface sends and expects space packets.
- (breaking) TCP: The TCP communication interface now expects a generic `Sequence[PacketId]`
  instead of a tuple of raw packet IDs. This makes usage more ergonomic.
- (possibly breaking): Rename `com_if` module to `com`.
- (breaking): `tmtccmd.tc.queue.DefaultPusQueueHelper`: The timestamp length of time tagged
  telecommands needs to be specified explicitely now (no default value of 4).

## Fixed

- TCP: Actually use the TM polling frequency parameter now in the TM reception thread.
- TCP: The `data_available` API now works properly by always converting the internal unparsed
  TM queue to the TM packet list and returning its length.

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
- (breaking) `pus_200_fsfw_mode`: Rename `Modes` to `Mode`.
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
