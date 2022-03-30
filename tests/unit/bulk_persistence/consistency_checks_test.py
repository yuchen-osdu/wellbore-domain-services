import pandas as pd
import pytest
from deepdiff import DeepDiff

from app.bulk_persistence.consistency_checks import DataConsistencyChecks




def test_get_data_columns_name():
    computed = DataConsistencyChecks._get_data_columns_name(
        ["GR[1]", "GR[2]", "DEN[1324]", "VSHALE[1324]", "", "A[1324][456]"]
    )

    assert not DeepDiff(computed, {"GR", "DEN", "VSHALE", "A[1324]"})

    assert DataConsistencyChecks._get_data_columns_name([]) == set()
    assert DataConsistencyChecks._get_data_columns_name([""]) == set()
    assert DataConsistencyChecks._get_data_columns_name(["[foo]"]) == {"[foo]"}
    assert DataConsistencyChecks._get_data_columns_name(["[1234]"]) == {"[1234]"}
