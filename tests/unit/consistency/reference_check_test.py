import pytest
import pandas as pd

from app.consistency.reference_check import (
    check_reference_is_strictly_monotonic,
    ReferenceCurveException,
    raise_if_dict_value_is_different,
    ColumnDescribe,
)


def test_check_reference_is_strictly_monotonic_success():
    check_reference_is_strictly_monotonic(ColumnDescribe.from_column(pd.DataFrame(), "MD"))
    check_reference_is_strictly_monotonic(ColumnDescribe.from_column(pd.DataFrame({"MD": [0, 1, 2, 3, 4]}), "MD"))
    check_reference_is_strictly_monotonic(ColumnDescribe.from_column(pd.DataFrame({"MD": [0]}), "MD"))


@pytest.mark.parametrize(
    "ref, error",
    [
        (pd.DataFrame({"MD": [0, 1, 1, 2, 3, 4]}), "Repeated values in a reference curve aren't allowed."),
        (pd.DataFrame({"MD": [0, None, 1, 2, 3, 4]}), "Nan values in a reference curve are not allowed."),
        (pd.DataFrame({"MD": [0, 2, 4, 3, 5]}), "Reference must be monotonically increasing or decreasing."),
    ],
)
def test_check_reference_is_strictly_monotonic_error(ref, error):
    with pytest.raises(ReferenceCurveException, match=f"^{error}$"):
        check_reference_is_strictly_monotonic(ColumnDescribe.from_column(ref, "MD"))


@pytest.mark.parametrize(
    "value_in_dict, reference_value",
    [
        (10.0, 10 + 1e-8),
        (10.0 + 1e-8, 10),
        ("10.0", 10 + 1e-8),
        ("10.0000001", 10),
    ],
)
def test_raise_if_dict_value_is_valid_not_close(value_in_dict, reference_value):
    attr_name = "CustomAttr"
    with pytest.raises(ReferenceCurveException):
        raise_if_dict_value_is_different(
            record_data={attr_name: value_in_dict}, attr_name=attr_name, reference_value=reference_value, error_msg=""
        )


@pytest.mark.parametrize(
    "data, attr_name, reference_value",
    [
        ({"TopMeasuredDepth": 0.0}, "TopMeasuredDepth", 0.0),
        ({"TopMeasuredDepth": "0.0"}, "TopMeasuredDepth", 0.0),
        ({"TopMeasuredDepth": 0.0}, "foo", 10.0),
        ({"TopMeasuredDepth": 10}, "TopMeasuredDepth", 10 + 1e-9),
        ({"TopMeasuredDepth": -10}, "TopMeasuredDepth", -10 + 1e-9),
        ({"TopMeasuredDepth": None}, "TopMeasuredDepth", 0.0),
        ({}, "TopMeasuredDepth", 0.0),
    ],
)
def test_raise_if_dict_value_is_different(data, attr_name, reference_value):
    try:
        raise_if_dict_value_is_different(
            record_data=data, attr_name=attr_name, reference_value=reference_value, error_msg=""
        )
    except ReferenceCurveException as exc:
        assert False, f"Should not raise ReferenceCurveException"


@pytest.mark.parametrize(
    "data, attr_name, reference_value, error_msg, expected",
    [
        (
            {"TopMeasuredDepth": 0.0},
            "TopMeasuredDepth",
            1.0,
            "Value ({reference_value}) is different from {attr_name} value ({attr_value}).",
            r"^Value \(1\.0\) is different from TopMeasuredDepth value \(0\.0\)\.$",
        ),
        (
            {"TopMeasuredDepth": 20.0},
            "TopMeasuredDepth",
            20 + 20 * 1e-9,
            "Value ({reference_value}) is different from {attr_name} value ({attr_value}).",
            r"^Value \(20\.00000002\) is different from TopMeasuredDepth value \(20\.0\)\.$",
        ),
        (
            {"TopMeasuredDepth": -20.0},
            "TopMeasuredDepth",
            20.0,
            "Value ({reference_value}) is different from {attr_name} value ({attr_value}).",
            r"^Value \(20\.0\) is different from TopMeasuredDepth value \(-20\.0\)\.$",
        ),
    ],
)
def test_check_top_bottom_reference_raise(data, attr_name, reference_value, error_msg, expected):
    with pytest.raises(ReferenceCurveException, match=expected):
        raise_if_dict_value_is_different(
            record_data=data, attr_name=attr_name, reference_value=reference_value, error_msg=error_msg
        )
