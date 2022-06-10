import pandas as pd
import pytest
from deepdiff import DeepDiff

from app.bulk_persistence.consistency_checks import DataConsistencyChecks




def test_get_curve_name_and_column_count():
    computed = DataConsistencyChecks._get_curve_name_and_column_count(
        ["GR", "GR[1]", "GR[2]",  "GR[0][1]", "DEN[1324]", "VSHALE[1324]", "", "A[1324][456]"]
    )

    assert not DeepDiff(computed, {"GR": 3, "GR[0]": 1, "DEN": 1, "VSHALE": 1, "A[1324]": 1})

    assert DataConsistencyChecks._get_curve_name_and_column_count([]) == {}
    assert DataConsistencyChecks._get_curve_name_and_column_count([""]) == {}
    assert DataConsistencyChecks._get_curve_name_and_column_count(["[foo]"]) == {"[foo]": 1}
    assert DataConsistencyChecks._get_curve_name_and_column_count(["[1234]"]) == {"[1234]": 1}
