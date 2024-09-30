# (C) Copyright 2024 European Centre for Medium-Range Weather Forecasts.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.


from anemoi.utils.sanetise import sanetise


def test_sanetise_urls():
    assert sanetise("http://johndoe:password@host:port/path") == "http://user:***@host:port/path"

    assert sanetise("http://www.example.com/path?pass=secret") == "http://www.example.com/path?pass=hidden"
    assert sanetise("http://www.example.com/path?password=secret") == "http://www.example.com/path?password=hidden"
    assert sanetise("http://www.example.com/path?token=secret") == "http://www.example.com/path?token=hidden"
    assert sanetise("http://www.example.com/path?user=secret") == "http://www.example.com/path?user=hidden"
    assert sanetise("http://www.example.com/path?key=secret") == "http://www.example.com/path?key=hidden"
    assert sanetise("http://www.example.com/path?pwd=secret") == "http://www.example.com/path?pwd=hidden"
    assert sanetise("http://www.example.com/path?_key=secret") == "http://www.example.com/path?_key=hidden"
    assert sanetise("http://www.example.com/path?_token=secret") == "http://www.example.com/path?_token=hidden"
    assert sanetise("http://www.example.com/path?apikey=secret") == "http://www.example.com/path?apikey=hidden"
    assert sanetise("http://www.example.com/path?api_key=secret") == "http://www.example.com/path?api_key=hidden"
    assert sanetise("http://www.example.com/path?api_token=secret") == "http://www.example.com/path?api_token=hidden"
    assert sanetise("http://www.example.com/path?_api_token=secret") == "http://www.example.com/path?_api_token=hidden"
    assert sanetise("http://www.example.com/path?_api_key=secret") == "http://www.example.com/path?_api_key=hidden"
    assert sanetise("http://www.example.com/path?username=secret") == "http://www.example.com/path?username=hidden"
    assert sanetise("http://www.example.com/path?login=secret") == "http://www.example.com/path?login=hidden"

    assert sanetise("http://www.example.com/path;pass=secret") == "http://www.example.com/path;pass=hidden"
    assert sanetise("http://www.example.com/path;password=secret") == "http://www.example.com/path;password=hidden"
    assert sanetise("http://www.example.com/path;token=secret") == "http://www.example.com/path;token=hidden"
    assert sanetise("http://www.example.com/path;user=secret") == "http://www.example.com/path;user=hidden"
    assert sanetise("http://www.example.com/path;key=secret") == "http://www.example.com/path;key=hidden"
    assert sanetise("http://www.example.com/path;pwd=secret") == "http://www.example.com/path;pwd=hidden"
    assert sanetise("http://www.example.com/path;_key=secret") == "http://www.example.com/path;_key=hidden"
    assert sanetise("http://www.example.com/path;_token=secret") == "http://www.example.com/path;_token=hidden"
    assert sanetise("http://www.example.com/path;apikey=secret") == "http://www.example.com/path;apikey=hidden"
    assert sanetise("http://www.example.com/path;api_key=secret") == "http://www.example.com/path;api_key=hidden"
    assert sanetise("http://www.example.com/path;api_token=secret") == "http://www.example.com/path;api_token=hidden"
    assert sanetise("http://www.example.com/path;_api_token=secret") == "http://www.example.com/path;_api_token=hidden"
    assert sanetise("http://www.example.com/path;_api_key=secret") == "http://www.example.com/path;_api_key=hidden"
    assert sanetise("http://www.example.com/path;username=secret") == "http://www.example.com/path;username=hidden"
    assert sanetise("http://www.example.com/path;login=secret") == "http://www.example.com/path;login=hidden"


def test_sanetise_paths():
    # We want to keep earthkit-data's url and path pattern

    assert sanetise("/home/johndoe/.ssh/id_rsa") == "/.../id_rsa"

    assert (
        sanetise("/data/model/{date:strftime(%Y)}/{date:strftime(%m)}/{date:strftime(%d)}/analysis.grib")
        == "/.../{date:strftime(%Y)}/{date:strftime(%m)}/{date:strftime(%d)}/analysis.grib"
    )

    assert sanetise("test.grib") == "test.grib"
    assert sanetise("../test.grib") == "../test.grib"
    assert sanetise("./test.grib") == "./test.grib"
    assert sanetise("sub/folder/test.grib") == "sub/folder/test.grib"
    assert sanetise("./folder/test.grib") == "./folder/test.grib"


if __name__ == "__main__":
    for name, obj in list(globals().items()):
        if name.startswith("test_") and callable(obj):
            print(f"Running {name}...")
            obj()
