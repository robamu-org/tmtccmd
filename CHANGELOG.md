Change Log
=======

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/)
and this project adheres to [Semantic Versioning](http://semver.org/).

## [unreleased]

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

## [v1.11.0]

### API Changes

- Improved API to specify handling for Service 3 and Service 8 packets in user hook object

## [v1.10.2]

- New API to build service/opcode dictionary
- Fixes for Service 8 Telemetry Parser

## [v1.10.1]

- Applied consistent formatting with `black` tool
- Some bugfixes for PUS packet stack
