import pytest
import pandas as pd

from app.bulk_persistence import ConsistencyException
from app.consistency.wellpressuretestrawmeasurement_consistency import (
    check_well_pressure_test_raw_measurement_consistency,
    WellPressureTestRawMeasurementConsistencyChecks,
    ColumnDoesNotMatchCurveIdException,
    TotalOfColumnsDoesNotMatchFieldNumberOfColumnsException,
)
from tests.unit.test_utils import make_record

MINIMAL_WELLPRESSURETESTRAWMEASUREMENTDATA_DATA = {
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
        (dict(MINIMAL_WELLPRESSURETESTRAWMEASUREMENTDATA_DATA, Curves=[{"CurveID": "curve-1"}, {"CurveID": "curve-1"}]), ConsistencyException),
    ]
)
def test_check_wellpressuretestrawmeasurement_consistency_invalid_cases(data, expected_exception):
    record = make_record(data=data)
    with pytest.raises(expected_exception):
        check_well_pressure_test_raw_measurement_consistency(record)

def test_check_wellpressuretestrawmeasurement_consistency_valid():
    record = make_record(data=MINIMAL_WELLPRESSURETESTRAWMEASUREMENTDATA_DATA)
    # Should not raise
    check_well_pressure_test_raw_measurement_consistency(record)


@pytest.mark.parametrize(
    "meta_curves,bulk_curves,expected_exception",
    [
        # No curves in meta, but columns present in bulk_info
        ([], {"col1": 1}, ColumnDoesNotMatchCurveIdException),
        # Curves in meta, but column name does not match any CurveID
        ([{"CurveID": "curve-1"}], {"col2": 1}, ColumnDoesNotMatchCurveIdException),
        # Curve present, but number of columns does not match
        ([{"CurveID": "curve-1", "NumberOfColumns": 2}], {"curve-1": 1}, TotalOfColumnsDoesNotMatchFieldNumberOfColumnsException),
    ]
)
def test_check_columns_consistency_negative(meta_curves, bulk_curves, expected_exception):
    meta = {"Curves": meta_curves}
    with pytest.raises(expected_exception):
        WellPressureTestRawMeasurementConsistencyChecks._check_columns_consistency(meta, bulk_curves)


def test_check_columns_consistency_positive():
    meta = {"Curves": [{"CurveID": "curve-1", "NumberOfColumns": 2}, {"CurveID": "curve-2"}]}
    bulk_curves = {"curve-1": 2, "curve-2": 1}
    # Should not raise
    WellPressureTestRawMeasurementConsistencyChecks._check_columns_consistency(meta, bulk_curves)


def test_check_bulk_consistency_on_post_bulk_valid():
    meta = {"Curves": [{"CurveID": "curve-1"}]}
    df = pd.DataFrame({"curve-1": [1, 2, 3]})
    record = make_record(data=meta)
    # Should not raise
    WellPressureTestRawMeasurementConsistencyChecks.check_bulk_consistency_on_post_bulk(record, df)


def test_check_bulk_consistency_on_post_bulk_no_data():
    meta = {}
    df = pd.DataFrame({"curve-1": [1, 2, 3]})
    record = make_record(data=meta)
    # Should not raise
    WellPressureTestRawMeasurementConsistencyChecks.check_bulk_consistency_on_post_bulk(record, df)