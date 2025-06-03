import pandas as pd
import pytest
from app.bulk_persistence.consistency_checks import (
    DataConsistencyChecks,
    ColumnDescribe,
    Monotonicity,
    BulkInfoForConsistency,
)
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
    assert ColumnDescribe.from_column(pd.DataFrame({"MD": [1, 2, 3]}), "MD").is_monotonic_increasing
    assert not ColumnDescribe.from_column(pd.DataFrame({"MD": [1, 2, 3]}), "MD").is_monotonic_decreasing
    assert ColumnDescribe(
        name="", monotonicity=Monotonicity.Decreasing, hasDuplicate=False, hasNan=False, startEnd={}
    ).is_monotonic_decreasing
    assert ColumnDescribe.model_validate_json(
        '{"name": "ref","monotonicity": "increasing", "hasDuplicate": false, "hasNan": false, "startEnd": {}}'
    ).is_monotonic_increasing
    assert ColumnDescribe.model_validate_json(
        '{"name": "ref","monotonicity": "decreasing", "hasDuplicate": false, "hasNan": false, "startEnd":{}}'
    ).is_monotonic_decreasing
    assert not ColumnDescribe.model_validate_json(
        '{"name": "ref", "hasDuplicate": false, "hasNan": false, "startEnd":{}}'
    ).is_monotonic_increasing
    assert ColumnDescribe.from_column(pd.DataFrame(), "MD").is_monotonic_increasing


@pytest.mark.parametrize(
    "ref, in_values, types",
    [
        (1.1, ["1.1", 1.1], ["float", "float32", "float64"]),
        (1, ["1", 1], ["int", "int32", "int64"]),
    ],
)
def test_column_describe_start_end_type(ref, in_values, types):
    for v in in_values:
        for t in types:
            d_input = {
                "dataType": t,
                "name": "ref",
                "hasDuplicate": False,
                "hasNan": False,
                "startEnd": {"columns": ["ref"], "data": [[v]]},
            }

            cd = ColumnDescribe(**d_input)
            assert np.isclose(ref, cd.start)
            assert np.isclose(cd.start, ref)
            assert np.isclose(ref, cd.end)
            assert np.isclose(cd.end, ref)


def test_bulk_info_for_consistency():
    obj = BulkInfoForConsistency.from_dataframe(pd.DataFrame())
    assert obj.index_start == ""
    assert obj.index_end == ""
    assert obj.index_type == ""

    obj = BulkInfoForConsistency.from_dataframe(pd.DataFrame({"MD": [17]}, index=[42]), "MD")
    assert obj.index_start == "42"
    assert obj.index_end == "42"
    assert "int" in obj.index_type
