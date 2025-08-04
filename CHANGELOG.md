# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Please add your functional changes to the appropriate section in the PR.
Keep it human-readable, your future self will thank you!

## [0.4.31](https://github.com/ecmwf/anemoi-utils/compare/0.4.30...0.4.31) (2025-08-04)


### Bug Fixes

* Remove too many warnings ([#193](https://github.com/ecmwf/anemoi-utils/issues/193)) ([df6862b](https://github.com/ecmwf/anemoi-utils/commit/df6862bf829e67651ccc97cbaac9f38096ad4d34))

## [0.4.30](https://github.com/ecmwf/anemoi-utils/compare/0.4.29...0.4.30) (2025-07-31)


### Bug Fixes

* Refactor code for casting dotdicts and apply this in getitem and setitem methods ([#169](https://github.com/ecmwf/anemoi-utils/issues/169)) ([e91aecf](https://github.com/ecmwf/anemoi-utils/commit/e91aecf6699a0daaed6f79e92b4ebc57cd4abe36))

## [0.4.29](https://github.com/ecmwf/anemoi-utils/compare/0.4.28...0.4.29) (2025-07-22)


### Features

* Better support for negative timedeltas ([#180](https://github.com/ecmwf/anemoi-utils/issues/180)) ([3f8041a](https://github.com/ecmwf/anemoi-utils/commit/3f8041a46b525b6fcbe6171cd8a8a40ec30b2c1f))
* **deps:** Use mlflow-skinny instead of mlflow ([#184](https://github.com/ecmwf/anemoi-utils/issues/184)) ([82e5c30](https://github.com/ecmwf/anemoi-utils/commit/82e5c3053962cd8e1e8f6a1ea9e8f92492e497b4))
* Protect mlflow token file ([#183](https://github.com/ecmwf/anemoi-utils/issues/183)) ([fdf0fc8](https://github.com/ecmwf/anemoi-utils/commit/fdf0fc84ee3e8076928f6c888374cd3aa008023b))
* **sanitise:** Sanitation level ([#175](https://github.com/ecmwf/anemoi-utils/issues/175)) ([8d85d8f](https://github.com/ecmwf/anemoi-utils/commit/8d85d8fd889bf72b8066cc021d4d7b329a360848))
* Support negative timedelta ([#178](https://github.com/ecmwf/anemoi-utils/issues/178)) ([546f6ec](https://github.com/ecmwf/anemoi-utils/commit/546f6ec76534cd39094957ce3b57b34f14f7a000))


### Bug Fixes

* Clean utils ([#185](https://github.com/ecmwf/anemoi-utils/issues/185)) ([de3c7a4](https://github.com/ecmwf/anemoi-utils/commit/de3c7a47f14c258997942564717c480caa124ee6))

## [0.4.28](https://github.com/ecmwf/anemoi-utils/compare/0.4.27...0.4.28) (2025-07-03)


### Features

* Migrate mlflow utils from anemoi-training ([#174](https://github.com/ecmwf/anemoi-utils/issues/174)) ([0b7767b](https://github.com/ecmwf/anemoi-utils/commit/0b7767bc23486b140ad7423e3c5c7d5857cef71c))


### Bug Fixes

* Treat mlflow as an optional dependency ([#177](https://github.com/ecmwf/anemoi-utils/issues/177)) ([feb1088](https://github.com/ecmwf/anemoi-utils/commit/feb1088169a29f42032bf26d5c43f9817557bafc))

## [0.4.27](https://github.com/ecmwf/anemoi-utils/compare/0.4.26...0.4.27) (2025-06-27)


### Features

* Split s3 config from s3 client code ([#170](https://github.com/ecmwf/anemoi-utils/issues/170)) ([56dacb1](https://github.com/ecmwf/anemoi-utils/commit/56dacb19efa0979acd72edb72a95f058b69d612a))

## [0.4.26](https://github.com/ecmwf/anemoi-utils/compare/0.4.25...0.4.26) (2025-06-25)


### Features

* Fixtures for temp dir handling for test data ([#166](https://github.com/ecmwf/anemoi-utils/issues/166)) ([2b9677f](https://github.com/ecmwf/anemoi-utils/commit/2b9677fffc5eba84876f974001b87b73c7e542af))
* Move anemoi-inference metadata command to this package, add metadata removal options ([#167](https://github.com/ecmwf/anemoi-utils/issues/167)) ([cabb989](https://github.com/ecmwf/anemoi-utils/commit/cabb989bdd4154a0476acf48e1ac44099c91c6db))

## [0.4.25](https://github.com/ecmwf/anemoi-utils/compare/0.4.24...0.4.25) (2025-06-24)


### Features

* Add a CLI to transfer data ([#164](https://github.com/ecmwf/anemoi-utils/issues/164)) ([3a845ca](https://github.com/ecmwf/anemoi-utils/commit/3a845ca0c31d115e6b3d0496d862a3eaee5fb236))
* Add function to test cli ([#168](https://github.com/ecmwf/anemoi-utils/issues/168)) ([9ac9b06](https://github.com/ecmwf/anemoi-utils/commit/9ac9b06b8fd0a62cad33ea5de6a6b482f0a13656))

## [0.4.24](https://github.com/ecmwf/anemoi-utils/compare/0.4.23...0.4.24) (2025-06-06)


### Features

* Add s3.object_exists() function ([#157](https://github.com/ecmwf/anemoi-utils/issues/157)) ([d898811](https://github.com/ecmwf/anemoi-utils/commit/d8988116320265dc6dfe467c57e0b6f29f76a2c1))
* Allow wildcard in config for matching s3 buckets to end points ([#160](https://github.com/ecmwf/anemoi-utils/issues/160)) ([ab20da7](https://github.com/ecmwf/anemoi-utils/commit/ab20da7e9497435a7183705b02dcbb7317d2700b))

## [0.4.23](https://github.com/ecmwf/anemoi-utils/compare/0.4.22...0.4.23) (2025-05-20)


### Bug Fixes

* fix list_folder on s3 ([#154](https://github.com/ecmwf/anemoi-utils/issues/154)) ([3ceb42c](https://github.com/ecmwf/anemoi-utils/commit/3ceb42c5185290d4c12e3fe90c3c331e3d8c7a5f))
* Remove the requirment to have git installed ([#149](https://github.com/ecmwf/anemoi-utils/issues/149)) ([88846e8](https://github.com/ecmwf/anemoi-utils/commit/88846e80be2927050a879ff953a78aecf39c3ac5))
* Use urllib to make _offline() aware of HTTP(s) proxies. ([#150](https://github.com/ecmwf/anemoi-utils/issues/150)) ([5c4d06f](https://github.com/ecmwf/anemoi-utils/commit/5c4d06f931590cc360eb4ffeeb8753a5d3d72bcb))

## [0.4.22](https://github.com/ecmwf/anemoi-utils/compare/0.4.21...0.4.22) (2025-04-10)


### Bug Fixes

* do not write to existing dir ([#148](https://github.com/ecmwf/anemoi-utils/issues/148)) ([38c6db6](https://github.com/ecmwf/anemoi-utils/commit/38c6db62c113e093d11c49b0fc398587ee89946c))
* remove archive file after unpacking ([#145](https://github.com/ecmwf/anemoi-utils/issues/145)) ([790e2a3](https://github.com/ecmwf/anemoi-utils/commit/790e2a3370db3d5c275f95b920926d5a01f894a7))

## [0.4.21](https://github.com/ecmwf/anemoi-utils/compare/0.4.20...0.4.21) (2025-04-07)


### Features

* allow temporary settings ([#143](https://github.com/ecmwf/anemoi-utils/issues/143)) ([38cefb5](https://github.com/ecmwf/anemoi-utils/commit/38cefb5c4ebd4e496d2c332e1d1d8b86d551615c))


### Bug Fixes

* pydantic schemas ([#141](https://github.com/ecmwf/anemoi-utils/issues/141)) ([c30f804](https://github.com/ecmwf/anemoi-utils/commit/c30f804012a4200eee69f5fb0708d4af760cb5f7))

## [0.4.20](https://github.com/ecmwf/anemoi-utils/compare/0.4.19...0.4.20) (2025-04-04)


### Features

* better message in testing ([#138](https://github.com/ecmwf/anemoi-utils/issues/138)) ([44f1638](https://github.com/ecmwf/anemoi-utils/commit/44f1638d64439af1e66f37f5e01f0cb4a384e175))

## [0.4.19](https://github.com/ecmwf/anemoi-utils/compare/0.4.18...0.4.19) (2025-04-04)


### Features

* more testing support functions ([#136](https://github.com/ecmwf/anemoi-utils/issues/136)) ([5687b87](https://github.com/ecmwf/anemoi-utils/commit/5687b87ed17748412340d00f0724249f59b4e3f2))


### Documentation

* add api ([#133](https://github.com/ecmwf/anemoi-utils/issues/133)) ([16af518](https://github.com/ecmwf/anemoi-utils/commit/16af5184eafbfc29cc3f0217a35675f2aa32847e))

## [0.4.18](https://github.com/ecmwf/anemoi-utils/compare/0.4.17...0.4.18) (2025-03-31)


### Features

* add matching rules ([#132](https://github.com/ecmwf/anemoi-utils/issues/132)) ([2382980](https://github.com/ecmwf/anemoi-utils/commit/2382980f4f53909a73fa0a5c8cfab108625f3c55))

## [0.4.17](https://github.com/ecmwf/anemoi-utils/compare/0.4.16...0.4.17) (2025-03-27)


### Features

* add generic env variables to override anemoi user config ([#128](https://github.com/ecmwf/anemoi-utils/issues/128)) ([fdc7248](https://github.com/ecmwf/anemoi-utils/commit/fdc72485616a0c092356a9ffa4cdca838a0c1a9d))


### Bug Fixes

* Iterate over copy of sys.modules. ([#127](https://github.com/ecmwf/anemoi-utils/issues/127)) ([7b0e7d0](https://github.com/ecmwf/anemoi-utils/commit/7b0e7d08264f7eb4c92fdcd744ff8c46eac82fb7))
* plugin name on error ([#120](https://github.com/ecmwf/anemoi-utils/issues/120)) ([a747f63](https://github.com/ecmwf/anemoi-utils/commit/a747f63d74bf1b108d913694915df59ffc4640c1))


### Documentation

* add links to GitHub  ([#123](https://github.com/ecmwf/anemoi-utils/issues/123)) ([cfe1ea2](https://github.com/ecmwf/anemoi-utils/commit/cfe1ea281e03a56b9a02108b6787c6c05b9518b0))
* Docathon ([#121](https://github.com/ecmwf/anemoi-utils/issues/121)) ([e1c9292](https://github.com/ecmwf/anemoi-utils/commit/e1c9292d65b1ffc8c9ce8eed41c7ffbe81f865a3))
* fix comment ([#125](https://github.com/ecmwf/anemoi-utils/issues/125)) ([ad3ed12](https://github.com/ecmwf/anemoi-utils/commit/ad3ed126f9a507dde7ce19064f1d32dae2cee6a3))

## [0.4.16](https://github.com/ecmwf/anemoi-utils/compare/0.4.15...0.4.16) (2025-03-22)


### Bug Fixes

* support plugin errors ([#118](https://github.com/ecmwf/anemoi-utils/issues/118)) ([1f0bb30](https://github.com/ecmwf/anemoi-utils/commit/1f0bb30d4d9441e6883c060e35fe4410f0c91833))

## [0.4.15](https://github.com/ecmwf/anemoi-utils/compare/0.4.14...0.4.15) (2025-03-21)


### Features

* accept hyphens in factory names ([#116](https://github.com/ecmwf/anemoi-utils/issues/116)) ([ada96e9](https://github.com/ecmwf/anemoi-utils/commit/ada96e911b592ff9d95d3a93fff5a6aa21cdebbe))

## [0.4.14](https://github.com/ecmwf/anemoi-utils/compare/0.4.13...0.4.14) (2025-03-21)


### Bug Fixes

* plugin support ([#110](https://github.com/ecmwf/anemoi-utils/issues/110)) ([329395a](https://github.com/ecmwf/anemoi-utils/commit/329395a5870cbf59bacb39cb5afea6b91c465b07))

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
