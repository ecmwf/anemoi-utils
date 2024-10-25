# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Please add your functional changes to the appropriate section in the PR.
Keep it human-readable, your future self will thank you!

## [Unreleased](https://github.com/ecmwf/anemoi-utils/compare/0.4.1...HEAD)

## [0.4.1](https://github.com/ecmwf/anemoi-utils/compare/0.4.0...0.4.1) - 2024-10-23

## Fixed
- Fix `__version__` import in init

### Changed
- Fix: resolve mounted filesystems in provenance
- Fix pre-commit regex
- ci: extend python versions [#23] (https://github.com/ecmwf/anemoi-utils/pull/23)
- Update copyright notice

## [0.4.0](https://github.com/ecmwf/anemoi-utils/compare/0.3.18...0.4.0) - 2024-10-11

### Added

- Add anemoi-transform link to documentation

## [0.3.17](https://github.com/ecmwf/anemoi-utils/compare/0.3.13...0.3.17) - 2024-10-01

### Added

- Codeowners file
- Pygrep precommit hooks
- Docsig precommit hooks
- Changelog merge strategy- Codeowners file
- Create dependency on wcwidth. MIT licence.
- Add distribution name dictionary to provenance [#15](https://github.com/ecmwf/anemoi-utils/pull/15) & [#19](https://github.com/ecmwf/anemoi-utils/pull/19)
- Add anonimize() function.

### Changed

- downstream-ci should only runs for changes in src and tests
- bugfixes for CI
- python3.9 support

### Removed

## [0.3.0] - Initial Release, utility functions

### Added

- Command line interface utility

## [0.2.0] - Initial Release, utility functions

### Changed

- updated documentation

## [0.1.0] - Initial Release, utility functions

### Added

- Documentation
- Initial implementation for a series of utility functions for used by the rest of the Anemoi packages

<!-- Add Git Diffs for Links above -->
https://github.com/ecmwf/anemoi-utils/compare/0.2.0...0.3.0
https://github.com/ecmwf/anemoi-utils/compare/0.1.0...0.2.0
[0.1.0]: https://github.com/ecmwf/anemoi-utils/releases/tag/0.1.0
