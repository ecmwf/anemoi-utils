# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Please add your functional changes to the appropriate section in the PR.
Keep it human-readable, your future self will thank you!

## [0.4.13](https://github.com/ecmwf/anemoi-utils/compare/0.4.12...0.4.13) (2025-03-14)


### Features

* add robust requests ([#112](https://github.com/ecmwf/anemoi-utils/issues/112)) ([5d87227](https://github.com/ecmwf/anemoi-utils/commit/5d87227e6f0b39f087f8a34f238806a2f73480f1))
* bugfix ([#100](https://github.com/ecmwf/anemoi-utils/issues/100)) ([c016cb4](https://github.com/ecmwf/anemoi-utils/commit/c016cb46c23b6a0575d9d843b06fd6b9f71b9f27))
* keep yaml formating in error messages ([#108](https://github.com/ecmwf/anemoi-utils/issues/108)) ([3bd6682](https://github.com/ecmwf/anemoi-utils/commit/3bd66828cf19d8e3d7d3fbed27533161b6285828))
* re-add default values in transfer function ([#101](https://github.com/ecmwf/anemoi-utils/issues/101)) ([6462205](https://github.com/ecmwf/anemoi-utils/commit/6462205ee25fa35a71af047b1fbb04bd3c4ca2c4))


### Bug Fixes

* add optional dependency. boto3 &lt;= 1.36 ([#105](https://github.com/ecmwf/anemoi-utils/issues/105)) ([c8c8393](https://github.com/ecmwf/anemoi-utils/commit/c8c8393ab1e886289541d3aa47a614afe5cd379b))


### Documentation

* update logo ([#96](https://github.com/ecmwf/anemoi-utils/issues/96)) ([c297127](https://github.com/ecmwf/anemoi-utils/commit/c297127e066c92023ca065b3e7d36ac4ab62527e))

## 0.4.12 (2025-01-30)

<!-- Release notes generated using configuration in .github/release.yml at main -->

## What's Changed
### Other Changes 🔗
* feat: better support for timedelta larger than 24h by @floriankrb in https://github.com/ecmwf/anemoi-utils/pull/81
* feat(requests): read input from stdin by @gmertes in https://github.com/ecmwf/anemoi-utils/pull/82
* chore: synced file(s) with ecmwf-actions/reusable-workflows by @DeployDuck in https://github.com/ecmwf/anemoi-utils/pull/80

## New Contributors
* @DeployDuck made their first contribution in https://github.com/ecmwf/anemoi-utils/pull/80

**Full Changelog**: https://github.com/ecmwf/anemoi-utils/compare/0.4.11...0.4.12

## 0.4.11 (2025-01-17)

<!-- Release notes generated using configuration in .github/release.yml at develop -->

## What's Changed
### Other Changes
* Feature request: Add option to read configuration from stdin by @mpartio in https://github.com/ecmwf/anemoi-utils/pull/59
* feat(plots): Add quick map plot for debugging by @b8raoult in https://github.com/ecmwf/anemoi-utils/pull/69
* feat: added-anemoi-utils-grids-and-tests by @floriankrb in https://github.com/ecmwf/anemoi-utils/pull/74
* feat(plot): added plotting options by @NRaoult in https://github.com/ecmwf/anemoi-utils/pull/72
* ci(release): Simplify Release Workflow to Minimum by @JesperDramsch in https://github.com/ecmwf/anemoi-utils/pull/78
* feat: adding-tools-for-grids by @floriankrb in https://github.com/ecmwf/anemoi-utils/pull/76

## New Contributors
* @mpartio made their first contribution in https://github.com/ecmwf/anemoi-utils/pull/59
* @NRaoult made their first contribution in https://github.com/ecmwf/anemoi-utils/pull/72

**Full Changelog**: https://github.com/ecmwf/anemoi-utils/compare/0.4.10...0.4.11

## [0.4.5](https://github.com/ecmwf/anemoi-utils/compare/0.4.4...0.4.5) - 2024-11-06

### What's Changed

* upload with ssh by @floriankrb in https://github.com/ecmwf/anemoi-utils/pull/25
* feat: Add aliases decorator by @HCookie in https://github.com/ecmwf/anemoi-utils/pull/40

**Full Changelog**: https://github.com/ecmwf/anemoi-utils/compare/0.4.4...0.4.5

## [0.4.4](https://github.com/ecmwf/anemoi-utils/compare/0.4.3...0.4.4) - 2024-11-01

## [0.4.3](https://github.com/ecmwf/anemoi-utils/compare/0.4.1...0.4.3) - 2024-10-26

## [0.4.2](https://github.com/ecmwf/anemoi-utils/compare/0.4.1...0.4.2) - 2024-10-25

### Added

- Add supporting_arrays to checkpoints
- Add factories registry
- Optional renaming of subcommands via `command` attribute [#34](https://github.com/ecmwf/anemoi-utils/pull/34)
- `skip_on_hpc` pytest marker for tests that should not be run on HPC [36](https://github.com/ecmwf/anemoi-utils/pull/36)

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
- Add CONTRIBUTORS.md (#33)

## [0.3.17](https://github.com/ecmwf/anemoi-utils/compare/0.3.13...0.3.17) - 2024-10-01

### Added

- Codeowners file
- Pygrep precommit hooks
- Docsig precommit hooks
- Changelog merge strategy- Codeowners file
- Create dependency on wcwidth. MIT licence.
- Add distribution name dictionary to provenance [#15](https://github.com/ecmwf/anemoi-utils/pull/15) & [#19](https://github.com/ecmwf/anemoi-utils/pull/19)
- Add anonymize() function.
- Add transfer to ssh:// target (experimental)
- Deprecated 'anemoi.utils.s3'

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
