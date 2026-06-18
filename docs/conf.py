# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import datetime
import os
import pathlib
import sys

read_the_docs_build = os.environ.get("READTHEDOCS", None) == "True"

sys.path.insert(0, os.path.join(os.path.abspath(".."), "src"))

# -- Auto-generate API stubs with sphinx-apidoc ------------------------------
# Run sphinx-apidoc at config time so the _api/ directory is always populated,
# regardless of whether a pre-build script ran.

_docs_dir = pathlib.Path(__file__).parent
_src_dir = _docs_dir.parent / "src"
_api_dir = _docs_dir / "_api"
_anemoi_pkg = _src_dir / "anemoi"

# Ensure the namespace package has an __init__.py for apidoc to traverse
_ns_init = _anemoi_pkg / "__init__.py"
_created_ns_init = False
if not _ns_init.exists():
    _ns_init.touch()
    _created_ns_init = True

try:
    from sphinx.ext.apidoc import main as apidoc_main

    apidoc_main(["-M", "-f", "-o", str(_api_dir), str(_anemoi_pkg)])
finally:
    if _created_ns_init:
        _ns_init.unlink(missing_ok=True)

# Write an index page that wraps the generated module tree under a proper
# "API" heading so it appears as a single collapsible sidebar entry.
(_api_dir / "index.rst").write_text("*****\n API\n*****\n\n.. toctree::\n   :maxdepth: 4\n\n   anemoi\n")

source_suffix = ".rst"
master_doc = "index"
pygments_style = "sphinx"
html_theme_options = {"logo_only": True}
html_logo = "_static/logo.png"


# -- Project information -----------------------------------------------------

project = "Anemoi Utils"

author = "Anemoi contributors"

year = datetime.datetime.now().year
if year == 2024:
    years = "2024"
else:
    years = f"2024-{year}"

copyright = f"{years}, Anemoi contributors"

try:
    from anemoi.utils._version import __version__

    release = __version__
except ImportError:
    release = "0.0.0"


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "sphinx.ext.todo",
    "sphinx_rtd_theme",
    "nbsphinx",
    "sphinx.ext.graphviz",
    "sphinx.ext.intersphinx",
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinxcontrib.autodoc_pydantic",
    "sphinxarg.ext",
]

# Add any paths that contain templates here, relative to this directory.
# templates_path = ["_templates"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = [
    "_build",
    "Thumbs.db",
    ".DS_Store",
    "'**.ipynb_checkpoints'",
    "_api/modules.rst",
]

intersphinx_mapping = {
    "python": ("https://python.readthedocs.io/en/latest", None),
    "anemoi-utils": (
        "https://anemoi-utils.readthedocs.io/en/latest/",
        ("../../anemoi-utils/docs/_build/html/objects.inv", None),
    ),
    "anemoi-datasets": (
        "https://anemoi-datasets.readthedocs.io/en/latest/",
        ("../../anemoi-datasets/docs/_build/html/objects.inv", None),
    ),
    "anemoi-models": (
        "https://anemoi-models.readthedocs.io/en/latest/",
        ("../../anemoi-models/docs/_build/html/objects.inv", None),
    ),
    "anemoi-training": (
        "https://anemoi-training.readthedocs.io/en/latest/",
        ("../../anemoi-training/docs/_build/html/objects.inv", None),
    ),
    "anemoi-inference": (
        "https://anemoi-inference.readthedocs.io/en/latest/",
        ("../../anemoi-inference/docs/_build/html/objects.inv", None),
    ),
    "anemoi-graphs": (
        "https://anemoi-graphs.readthedocs.io/en/latest/",
        ("../../anemoi-graphs/docs/_build/html/objects.inv", None),
    ),
    "anemoi-registry": (
        "https://anemoi-registry.readthedocs.io/en/latest/",
        ("../../anemoi-registry/docs/_build/html/objects.inv", None),
    ),
    "anemoi-transform": (
        "https://anemoi-transform.readthedocs.io/en/latest/",
        ("../../anemoi-transform/docs/_build/html/objects.inv", None),
    ),
    "anemoi-plugins": (
        "https://anemoi-plugins.readthedocs.io/en/latest/",
        ("../../anemoi-plugins/docs/_build/html/objects.inv", None),
    ),
}

# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = "sphinx_rtd_theme"

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ["_static"]
html_css_files = ["style.css"]


todo_include_todos = not read_the_docs_build

autodoc_member_order = "bysource"  # Keep file order

# -- autodoc-pydantic configuration ------------------------------------------
# Show field docstrings, defaults, aliases, and env variable names
autodoc_pydantic_model_show_json = False
autodoc_pydantic_model_show_config_summary = False
autodoc_pydantic_model_show_field_summary = True
autodoc_pydantic_model_show_validator_summary = False
autodoc_pydantic_model_show_validator_members = False
autodoc_pydantic_model_member_order = "bysource"
autodoc_pydantic_model_undoc_members = False

autodoc_pydantic_settings_show_json = False
autodoc_pydantic_settings_show_config_summary = False
autodoc_pydantic_settings_show_field_summary = True
autodoc_pydantic_settings_show_validator_summary = False
autodoc_pydantic_settings_show_validator_members = False
autodoc_pydantic_settings_member_order = "bysource"
autodoc_pydantic_settings_undoc_members = False

autodoc_pydantic_field_show_alias = True
autodoc_pydantic_field_list_validators = False
autodoc_pydantic_field_show_default = True

html_context = {
    "display_github": True,
    "github_user": "ecmwf",
    "github_repo": "anemoi-utils",
    "github_version": "main/docs/",
}
