import pytest
import pandas as pd
from app.consistency.ppfgdataset_consistency import (
    check_ppfgdataset_consistency,
    DuplicatedCurveIdException,
    PrimaryReferenceCurveIdNotFoundException,
    ContextTypeIdMissingException,
    ReferenceWellTrajectoryIdMissingException,
    PPFGDatasetConsistencyChecks,
    ColumnDoesNotMatchCurveIdException,
)
from tests.unit.test_utils import make_record

MINIMAL_PPFG_DATA = {
    "ContextTypeID": "context-1",
    "ReferenceWellTrajectoryID": "trajectory-1",
    "PrimaryReferenceCurveID": "curve-1",
    "Curves": [
        {"CurveID": "curve-1"},
        {"CurveID": "curve-2"}
    ]
}

@pytest.mark.parametrize(
    "data,expected_exception",
    [
        (dict(MINIMAL_PPFG_DATA ,ContextTypeID = None), ContextTypeIdMissingException),
        (dict(MINIMAL_PPFG_DATA, ReferenceWellTrajectoryID= None), ReferenceWellTrajectoryIdMissingException),
        (dict(MINIMAL_PPFG_DATA, Curves=[{"CurveID": "curve-1"}, {"CurveID": "curve-1"}]), DuplicatedCurveIdException),
        (dict(MINIMAL_PPFG_DATA, PrimaryReferenceCurveID="curve-x"), PrimaryReferenceCurveIdNotFoundException),
    ]
)
def test_check_ppfgdataset_consistency_invalid_cases(data, expected_exception):
    record = make_record(data=data)
    with pytest.raises(expected_exception):
        check_ppfgdataset_consistency(record)

def test_check_ppfgdataset_consistency_valid():
    record = make_record(data=MINIMAL_PPFG_DATA)
    # Should not raise
    check_ppfgdataset_consistency(record)

@pytest.mark.parametrize(
    "record_data,bulk_info_curves",
    [
        # No curves in meta, but columns present in bulk_info
        ({}, {"col1": 1}),
        # Curves in meta, but column name does not match any CurveID
        ({"Curves": [{"CurveID": "curve-1"}]}, {"col2": 1}),
    ]
)
def test_check_columns_consistency_raises(record_data, bulk_info_curves):
    with pytest.raises(ColumnDoesNotMatchCurveIdException):
        PPFGDatasetConsistencyChecks._check_columns_consistency(record_data, bulk_info_curves)

def test_check_bulk_consistency_on_post_bulk_valid():
    record = make_record(data = dict(MINIMAL_PPFG_DATA))
    df = pd.DataFrame({"curve-1": [1, 2, 3]})
    # Should not raise
    PPFGDatasetConsistencyChecks.check_bulk_consistency_on_post_bulk(record, df)

def test_check_bulk_consistency_on_post_bulk_no_data():
    record = make_record(data=dict())
    df = pd.DataFrame({"curve-1": [1, 2, 3]})
    assert PPFGDatasetConsistencyChecks.check_bulk_consistency_on_post_bulk(record, df) is None

def test_get_reference_curve():
    record = make_record(data=dict(MINIMAL_PPFG_DATA))
    assert PPFGDatasetConsistencyChecks.get_reference_curve(record) == "curve-1"