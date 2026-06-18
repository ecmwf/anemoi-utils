.. _anemoi-utils:

.. _index-page:

##########################################
 Welcome to `anemoi-utils` documentation!
##########################################

*Anemoi* is a framework for developing machine learning weather
forecasting models. It comprises of components or packages for preparing
training datasets, conducting ML model training and a registry for
datasets and trained models. *Anemoi* provides tools for operational
inference, including interfacing to verification software. As a
framework it seeks to handle many of the complexities that
meteorological organisations will share, allowing them to easily train
models from existing recipes but with their own data.

``anemoi-utils`` is the shared utility layer that the rest of the Anemoi
packages depend on. It provides:

Configuration & settings
   A Pydantic-settings based configuration system that loads from
   TOML/YAML files and environment variables, with built-in secret
   management. See :doc:`modules/settings` for the full schema
   reference and environment variable naming conventions.

Checkpoint I/O
   Read and write extra metadata inside PyTorch checkpoint files
   (zip archives). See :doc:`modules/checkpoints`.

Date & frequency handling
   Normalise frequencies, generate date ranges, and parse date
   specifications used across Anemoi workflows. See
   :doc:`modules/dates`.

GRIB parameter database
   Look up GRIB parameter metadata from the ECMWF parameter database,
   with local caching support. See :doc:`modules/grib`.

Human-readable formatting
   Convert bytes, seconds, and other quantities into human-friendly
   strings. See :doc:`modules/humanize`.

Provenance tracking
   Collect environment information (Python version, installed packages,
   git state) for experiment reproducibility. See
   :doc:`modules/provenance`.

S3 / object storage
   Helpers for interacting with S3-compatible object storage, including
   per-bucket credential overrides. See :doc:`modules/s3`.

Testing utilities
   Shared test helpers and fixtures used across Anemoi packages. See
   :doc:`modules/testing`.

Text & table formatting
   Terminal-friendly text utilities including table rendering, dotted
   lines, and tree display. See :doc:`modules/text`.

.. toctree::
   :maxdepth: 1
   :caption: Getting Started
   :hidden:

   installing

.. toctree::
   :maxdepth: 1
   :caption: Configuration
   :hidden:

   modules/settings

.. toctree::
   :maxdepth: 1
   :caption: Modules
   :hidden:

   modules/checkpoints
   modules/dates
   modules/grib
   modules/humanize
   modules/provenance
   modules/s3
   modules/testing
   modules/text

.. toctree::
   :maxdepth: 2
   :caption: API Reference
   :hidden:

   _api/index

.. toctree::
   :maxdepth: 1
   :caption: Links
   :hidden:

   Anemoi <https://anemoi.readthedocs.io>
   Source code <https://github.com/ecmwf/anemoi-utils>
   Issues <https://github.com/ecmwf/anemoi-utils/issues>

*********
 License
*********

*Anemoi* is available under the open source `Apache License`__.

.. __: http://www.apache.org/licenses/LICENSE-2.0.html
