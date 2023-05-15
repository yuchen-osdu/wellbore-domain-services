import pandas as pd
import pytest
from app.bulk_persistence.consistency_checks import DataConsistencyChecks, ColumnDescribe, Monotonicity
import numpy as np


def test_get_curve_name_and_column_count():
    computed = DataConsistencyChecks._get_curve_name_and_column_count(
        ["GR", "GR[1]", "GR[2]", "GR[0][1]", "DEN[1324]", "VSHALE[1324]", "", "A[1324][456]"]
    )

    assert computed == {"GR": 3, "GR[0]": 1, "DEN": 1, "VSHALE": 1, "A[1324]": 1}

    assert DataConsistencyChecks._get_curve_name_and_column_count([]) == {}
    assert DataConsistencyChecks._get_curve_name_and_column_count([""]) == {}
    assert DataConsistencyChecks._get_curve_name_and_column_count(["[foo]"]) == {"[foo]": 1}
    assert DataConsistencyChecks._get_curve_name_and_column_count(["[1234]"]) == {"[1234]": 1}


def test_column_describe_monotonicity():
    assert ColumnDescribe.from_series(pd.Series()).is_monotonic_increasing
    assert ColumnDescribe.from_series(pd.DataFrame({"MD": [1, 2, 3]})["MD"]).is_monotonic_increasing
    assert not ColumnDescribe.from_series(pd.DataFrame({"MD": [1, 2, 3]})["MD"]).is_monotonic_decreasing
    assert ColumnDescribe(
        name="", monotonicity=Monotonicity.MonotonicDecreasing, hasDuplicate=False, hasNan=False
    ).is_monotonic_decreasing
    assert ColumnDescribe.parse_raw(
        '{"name": "ref","monotonicity": "increasing", "hasDuplicate": false, "hasNan": false}'
    ).is_monotonic_increasing
    assert ColumnDescribe.parse_raw(
        '{"name": "ref","monotonicity": "decreasing", "hasDuplicate": false, "hasNan": false}'
    ).is_monotonic_decreasing
    assert not ColumnDescribe.parse_raw(
        '{"name": "ref", "hasDuplicate": false, "hasNan": false}'
    ).is_monotonic_increasing


@pytest.mark.parametrize("ref, in_values, types", [
    (1.1, ["1.1", 1.1], ["float", "float32", "float64"]),
    (1, ["1", 1], ["int", "int32", "int64"]),
])
def test_column_describe_start_end_type(ref, in_values, types):
    for v in in_values:
        for t in types:
            d_input = {
                "start": v,
                "end": v,
                "type": t,
                "name": "ref",
                "hasDuplicate": False,
                "hasNan": False
            }

            cd = ColumnDescribe(**d_input)
            assert np.isclose(ref, cd.start)
            assert np.isclose(cd.start, ref)
            assert np.isclose(ref, cd.end)
            assert np.isclose(cd.end, ref)
