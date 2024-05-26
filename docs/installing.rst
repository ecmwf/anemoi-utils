Installing
==========

To install the package, you can use the following command:

.. code-block:: bash

    pip install anemoi-utils[...options...]

The options are:

- ``dev``: install the development dependencies
- ``all``: install all the dependencies
- ``text``: install the dependencies for text processing
- ``provenance``: install the dependencies for provenance tracking
- ``grib``: install the dependencies for looking up GRIB parameters

Contributing
------------

.. code-block:: bash

    git clone ...
    cd anemoi-utils
    pip install .[dev]
    pip install -r docs/requirements.txt

You may also have to install pandoc on MacOS:

.. code-block:: bash

    brew install pandoc
