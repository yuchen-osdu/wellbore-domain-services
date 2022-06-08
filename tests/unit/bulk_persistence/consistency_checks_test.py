import pandas as pd
import pytest
from deepdiff import DeepDiff

from app.bulk_persistence.consistency_checks import DataConsistencyChecks




def test_get_name_and_count_data_columns():
    computed = DataConsistencyChecks._get_name_and_count_data_columns(
        ["GR[1]", "GR[2]", "DEN[1324]", "VSHALE[1324]", "", "A[1324][456]"]
    )

    assert not DeepDiff(computed, {"GR": 2, "DEN": 1, "VSHALE": 1, "A[1324]": 1})

    assert DataConsistencyChecks._get_name_and_count_data_columns([]) == {}
    assert DataConsistencyChecks._get_name_and_count_data_columns([""]) == {}
    assert DataConsistencyChecks._get_name_and_count_data_columns(["[foo]"]) == {"[foo]": 1}
    assert DataConsistencyChecks._get_name_and_count_data_columns(["[1234]"]) == {"[1234]": 1}
