# (C) Copyright 2026 Anemoi contributors.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import argparse
import json

import pytest

from anemoi.utils.nexus import add_nexus_record_arguments
from anemoi.utils.nexus import load_attributes
from anemoi.utils.nexus import nexus_record
from anemoi.utils.nexus import normalise_attributes
from anemoi.utils.nexus import record_attributes
from anemoi.utils.nexus import write_nexus_record


def _parse(argv):
    parser = argparse.ArgumentParser()
    add_nexus_record_arguments(parser)
    return parser.parse_args(argv)


def test_singular_and_plural_spellings() -> None:
    assert normalise_attributes({"project": "MLP", "license": "CC-BY-4.0", "owner": "alice"}) == {
        "projects": ["MLP"],
        "licenses": ["CC-BY-4.0"],
        "owner": "alice",
    }
    assert normalise_attributes({"projects": ["A", "B"], "licences": "X, Y", "description": "d"}) == {
        "projects": ["A", "B"],
        "licenses": ["X", "Y"],
        "description": "d",
    }
    with pytest.raises(ValueError, match="another spelling"):
        normalise_attributes({"project": "A", "projects": ["B"]})
    with pytest.raises(ValueError, match="a name or a list of names"):
        normalise_attributes({"projects": [1, 2]})


def test_attributes_file_json_or_yaml(tmp_path) -> None:
    y = tmp_path / "attrs.yaml"
    y.write_text("owner: alice\nproject: MLP\nlicenses: [CC-BY-4.0]\n")
    assert load_attributes(f"@{y}") == {
        "owner": "alice",
        "projects": ["MLP"],
        "licenses": ["CC-BY-4.0"],
    }
    j = tmp_path / "attrs.json"
    j.write_text(json.dumps({"projects": ["A"], "licence": "X"}))
    assert load_attributes(str(j)) == {"projects": ["A"], "licenses": ["X"]}
    (tmp_path / "list.yaml").write_text("- a\n")
    with pytest.raises(ValueError, match="object"):
        load_attributes(str(tmp_path / "list.yaml"))


def test_options_win_over_the_file(tmp_path) -> None:
    f = tmp_path / "attrs.yaml"
    f.write_text("owner: alice\nprojects: [A]\nlicense: X\ndescription: from the file\n")
    args = _parse([f"@{f}", "--owner", "bob", "--projects", "P,Q", "--project", "R"])
    assert record_attributes(args) == {
        "owner": "bob",
        "projects": ["P", "Q", "R"],
        "licenses": ["X"],
        "description": "from the file",
    }
    assert record_attributes(_parse(["--license", "Y", "--name", "ds"])) == {
        "licenses": ["Y"],
        "name": "ds",
    }
    with pytest.raises(ValueError, match="@FILE"):
        record_attributes(_parse([str(f)]))


def test_record_and_output(tmp_path, capsys) -> None:
    record = nexus_record(
        uuid="u1",
        name="ds",
        metadata={"uuid": "u1"},
        attributes={"name": "other", "owner": "a"},
    )
    assert record == {
        "uuid": "u1",
        "name": "other",
        "metadata": {"uuid": "u1"},
        "owner": "a",
    }
    assert "name" not in nexus_record(uuid="u2", metadata={})
    with pytest.raises(ValueError, match="from the asset"):
        nexus_record(uuid="u1", metadata={}, attributes={"uuid": "u9"})
    write_nexus_record(record)
    assert json.loads(capsys.readouterr().out) == record
    out = tmp_path / "record.json"
    write_nexus_record(record, str(out))
    assert json.loads(out.read_text()) == record
