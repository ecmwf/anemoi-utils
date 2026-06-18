.. _settings-reference:

##########
 Settings
##########

Anemoi uses `pydantic-settings <https://docs.pydantic.dev/latest/concepts/pydantic_settings/>`_
to manage configuration. Every setting can be configured via a TOML/YAML
config file **or** overridden at runtime with an environment variable.

Configuration files
===================

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - File
     - Purpose
   * - ``~/.config/anemoi/settings.toml``
     - Main configuration (non-secret values)
   * - ``~/.config/anemoi/settings.yaml``
     - Alternative YAML format for main configuration
   * - ``~/.config/anemoi/settings.secrets.toml``
     - Secret values (must be mode ``0600``)
   * - ``~/.config/anemoi/settings.secrets.yaml``
     - Alternative YAML format for secrets

Override the file location by setting the ``ANEMOI_SETTINGS_FILE``
environment variable.

Loading priority
================

Settings are loaded with the following priority (highest first):

1. Environment variables (``ANEMOI_SETTINGS_*``)
2. Secrets file (``settings.secrets.toml`` / ``settings.secrets.yaml``)
3. Main config file (``settings.toml`` / ``settings.yaml``)
4. Default values defined in the schema

Environment variables
=====================

All settings can be overridden using environment variables. The naming
convention is::

   ANEMOI_SETTINGS_<SECTION>__<KEY>=<value>

Sections and keys are **upper-cased**, underscores in field names stay as
single underscores, and nested sections use **double underscores**
(``__``) as separators.

Examples
--------

**Object storage endpoint**

The TOML key ``endpoint-url`` in section ``[object-storage]`` maps to
field name ``endpoint_url`` on ``ObjectStorageConfig``. The environment
variable is built as ``ANEMOI_SETTINGS_`` + ``OBJECT_STORAGE`` + ``__``
+ ``ENDPOINT_URL``:

.. code-block:: bash

   # Set the global S3 endpoint
   export ANEMOI_SETTINGS_OBJECT_STORAGE__ENDPOINT_URL="https://s3.example.com"

**Object storage credentials (secrets)**

Secret fields follow the same naming. The field ``access_key_id`` on
``ObjectStorageConfig`` becomes:

.. code-block:: bash

   # Override the S3 access key at runtime
   export ANEMOI_SETTINGS_OBJECT_STORAGE__ACCESS_KEY_ID="AKIA..."
   export ANEMOI_SETTINGS_OBJECT_STORAGE__SECRET_ACCESS_KEY="wJalr..."

.. note::

   For persistent secret storage, prefer the ``settings.secrets.toml``
   file (mode ``0600``) over environment variables to avoid secrets
   leaking into process listings or shell history.

**Dataset search paths**

List fields are set as JSON-encoded arrays:

.. code-block:: bash

   # Add dataset search paths
   export ANEMOI_SETTINGS_DATASETS__PATH='["/data/zarr", "s3://bucket/datasets"]'

**Boolean flags**

.. code-block:: bash

   # Skip dataset naming convention checks
   export ANEMOI_SETTINGS_DATASETS__IGNORE_NAMING_CONVENTIONS="true"

   # Use search-path fallback when a .zarr path is not found
   export ANEMOI_SETTINGS_DATASETS__USE_SEARCH_PATH_NOT_FOUND="true"

**ParamDB settings**

.. code-block:: bash

   # Change the default GRIB parameter origin
   export ANEMOI_SETTINGS_PARAMDB__DEFAULT_ORIGIN="ecmf"

   # Extend the parameter cache lifetime to 90 days
   export ANEMOI_SETTINGS_PARAMDB__CACHE_LENGTH="90"

**Utils -- custom grids directory**

.. code-block:: bash

   export ANEMOI_SETTINGS_UTILS__GRIDS_PATH="~/my-grids"

**Custom settings file location**

This is a standalone variable (not part of the nested schema) that
controls which configuration file is loaded:

.. code-block:: bash

   # Load settings from a project-specific file instead of the default
   export ANEMOI_SETTINGS_FILE="/project/config/anemoi-settings.toml"

**Slurm / batch job usage**

Environment variables are particularly useful in batch jobs where you
cannot modify config files on shared filesystems:

.. code-block:: bash

   #!/bin/bash
   #SBATCH --job-name=anemoi-train

   export ANEMOI_SETTINGS_OBJECT_STORAGE__ENDPOINT_URL="https://s3.internal.hpc"
   export ANEMOI_SETTINGS_DATASETS__PATH='["/scratch/datasets"]'
   export ANEMOI_SETTINGS_PARAMDB__CACHE_LENGTH="7"

   srun python -m anemoi.training ...

Settings schema reference
=========================

The reference below is auto-generated from the Pydantic schema.

AnemoiSettings
--------------

.. autopydantic_settings:: anemoi.utils.settings.AnemoiSettings
   :members:
   :inherited-members: BaseModel
   :undoc-members: False
   :no-index:

Object storage -- ``[object-storage]``
--------------------------------------

.. autopydantic_model:: anemoi.utils.settings_schema.object_storage.ObjectStorageConfig
   :members:
   :inherited-members: BaseModel
   :undoc-members: False
   :no-index:

.. autopydantic_model:: anemoi.utils.settings_schema.object_storage.ObjectStorageBucketConfig
   :members:
   :inherited-members: BaseModel
   :undoc-members: False
   :no-index:

Datasets -- ``[datasets]``
--------------------------

.. autopydantic_model:: anemoi.utils.settings_schema.datasets.DatasetsConfig
   :members:
   :inherited-members: BaseModel
   :undoc-members: False
   :no-index:

.. autopydantic_model:: anemoi.utils.settings_schema.datasets.DatasetsNamedConfig
   :members:
   :inherited-members: BaseModel
   :undoc-members: False
   :no-index:

ParamDB -- ``[paramdb]``
------------------------

.. autopydantic_model:: anemoi.utils.settings_schema.paramdb.ParamDBConfig
   :members:
   :inherited-members: BaseModel
   :undoc-members: False
   :no-index:

Utils -- ``[utils]``
--------------------

.. autopydantic_model:: anemoi.utils.settings_schema.utils.UtilsConfig
   :members:
   :inherited-members: BaseModel
   :undoc-members: False
   :no-index:
