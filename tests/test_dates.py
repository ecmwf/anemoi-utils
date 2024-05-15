from textwrap import dedent

import yaml

from anemoi.utils.dates import datetimes_factory


def _(txt):
    txt = dedent(txt)
    config = yaml.safe_load(txt)
    config = config["dates"]
    return datetimes_factory(config)


def test_date_1():
    d = _(
        """
        dates:
            - 2023-01-01
            - 2023-01-02
            - 2023-01-03
    """
    )
    assert len(list(d)) == 3


def test_date_2():
    d = _(
        """
        dates:
          start: 2023-01-01
          end: 2023-01-07
          frequency: 12
          day_of_week: [monday, friday]
    """
    )
    assert len(list(d)) == 4


def test_date_3():
    d = _(
        """
        dates:
          - start: 2023-01-01
            end: 2023-01-03
            frequency: 24
          - start: 2024-01-01T06:00:00
            end: 2024-01-03T18:00:00
            frequency: 6
    """
    )
    assert len(list(d)) == 14


def test_date_hindcast_1():
    d = _(
        """
        dates:
          - name: hindcast
            reference_dates:
              start: 2023-01-01
              end: 2023-01-03
              frequency: 24
            years: 20
    """
    )
    assert len(list(d)) == 60


def test_date_hindcast_2():
    d = _(
        """
        dates:
          - name: hindcast
            reference_dates:
              start: 2023-01-01
              end: 2023-01-03
              frequency: 24
            years: [2018, 2019, 2020, 2021]
    """
    )
    assert len(list(d)) == 12


if __name__ == "__main__":
    test_functions = [
        obj for name, obj in globals().items() if name.startswith("test_") and isinstance(obj, type(lambda: 0))
    ]
    for test_func in test_functions:
        print(f"Running test: {test_func.__name__}")
        test_func()
    print("All tests passed!")
