import pytest

from app.bulk_persistence import ConsistencyException
from app.consistency.wellpressuretestrawmeasurement_consistency import check_well_pressure_test_raw_measurement_consistency
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