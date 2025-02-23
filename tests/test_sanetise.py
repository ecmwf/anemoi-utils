# (C) Copyright 2024 Anemoi contributors.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.


from anemoi.utils.sanitise import sanitise


def test_sanitise_urls() -> None:
    """Test the sanitise function for sanitizing URLs with sensitive information."""
    assert sanitise("http://johndoe:password@host:port/path") == "http://user:***@host:port/path"

    assert sanitise("http://www.example.com/path?pass=secret") == "http://www.example.com/path?pass=hidden"
    assert sanitise("http://www.example.com/path?password=secret") == "http://www.example.com/path?password=hidden"
    assert sanitise("http://www.example.com/path?token=secret") == "http://www.example.com/path?token=hidden"
    assert sanitise("http://www.example.com/path?user=secret") == "http://www.example.com/path?user=hidden"
    assert sanitise("http://www.example.com/path?key=secret") == "http://www.example.com/path?key=hidden"
    assert sanitise("http://www.example.com/path?pwd=secret") == "http://www.example.com/path?pwd=hidden"
    assert sanitise("http://www.example.com/path?_key=secret") == "http://www.example.com/path?_key=hidden"
    assert sanitise("http://www.example.com/path?_token=secret") == "http://www.example.com/path?_token=hidden"
    assert sanitise("http://www.example.com/path?apikey=secret") == "http://www.example.com/path?apikey=hidden"
    assert sanitise("http://www.example.com/path?api_key=secret") == "http://www.example.com/path?api_key=hidden"
    assert sanitise("http://www.example.com/path?api_token=secret") == "http://www.example.com/path?api_token=hidden"
    assert sanitise("http://www.example.com/path?_api_token=secret") == "http://www.example.com/path?_api_token=hidden"
    assert sanitise("http://www.example.com/path?_api_key=secret") == "http://www.example.com/path?_api_key=hidden"
    assert sanitise("http://www.example.com/path?username=secret") == "http://www.example.com/path?username=hidden"
    assert sanitise("http://www.example.com/path?login=secret") == "http://www.example.com/path?login=hidden"

    assert sanitise("http://www.example.com/path;pass=secret") == "http://www.example.com/path;pass=hidden"
    assert sanitise("http://www.example.com/path;password=secret") == "http://www.example.com/path;password=hidden"
    assert sanitise("http://www.example.com/path;token=secret") == "http://www.example.com/path;token=hidden"
    assert sanitise("http://www.example.com/path;user=secret") == "http://www.example.com/path;user=hidden"
    assert sanitise("http://www.example.com/path;key=secret") == "http://www.example.com/path;key=hidden"
    assert sanitise("http://www.example.com/path;pwd=secret") == "http://www.example.com/path;pwd=hidden"
    assert sanitise("http://www.example.com/path;_key=secret") == "http://www.example.com/path;_key=hidden"
    assert sanitise("http://www.example.com/path;_token=secret") == "http://www.example.com/path;_token=hidden"
    assert sanitise("http://www.example.com/path;apikey=secret") == "http://www.example.com/path;apikey=hidden"
    assert sanitise("http://www.example.com/path;api_key=secret") == "http://www.example.com/path;api_key=hidden"
    assert sanitise("http://www.example.com/path;api_token=secret") == "http://www.example.com/path;api_token=hidden"
    assert sanitise("http://www.example.com/path;_api_token=secret") == "http://www.example.com/path;_api_token=hidden"
    assert sanitise("http://www.example.com/path;_api_key=secret") == "http://www.example.com/path;_api_key=hidden"
    assert sanitise("http://www.example.com/path;username=secret") == "http://www.example.com/path;username=hidden"
    assert sanitise("http://www.example.com/path;login=secret") == "http://www.example.com/path;login=hidden"


def test_sanitise_paths() -> None:
    """Test the sanitise function for sanitizing file paths."""
    # We want to keep earthkit-data's url and path pattern

    assert sanitise("/home/johndoe/.ssh/id_rsa") == "/.../id_rsa"

    assert (
        sanitise("/data/model/{date:strftime(%Y)}/{date:strftime(%m)}/{date:strftime(%d)}/analysis.grib")
        == "/.../{date:strftime(%Y)}/{date:strftime(%m)}/{date:strftime(%d)}/analysis.grib"
    )

    assert sanitise("test.grib") == "test.grib"
    assert sanitise("../test.grib") == "../test.grib"
    assert sanitise("./test.grib") == "./test.grib"
    assert sanitise("sub/folder/test.grib") == "sub/folder/test.grib"
    assert sanitise("./folder/test.grib") == "./folder/test.grib"


if __name__ == "__main__":
    for name, obj in list(globals().items()):
        if name.startswith("test_") and callable(obj):
            print(f"Running {name}...")
            obj()
