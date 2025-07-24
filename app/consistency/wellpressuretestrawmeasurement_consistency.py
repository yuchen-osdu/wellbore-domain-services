from fastapi import HTTPException, status
from odes_storage.models import Record

from app.bulk_persistence import ConsistencyException
from app.consistency.unique import get_unique_dict_attr_values
from app.helper.traces_ot import get_tracer

_tracer = get_tracer()

class DuplicatedCurveIdException(ConsistencyException):
    """raised if all curveID values are not unique"""

@_tracer.start_as_current_span("wellpressuretestrawmeasurement_consistency")
def check_well_pressure_test_raw_measurement_consistency(well_pressure_test_raw_measurement_data: Record):
    if not well_pressure_test_raw_measurement_data.data:
        # No Data to check
        return

    curves = well_pressure_test_raw_measurement_data.data.get("Curves", [])

    _ , duplicated_error = get_unique_dict_attr_values(curves, "CurveID")
    if duplicated_error:
        raise DuplicatedCurveIdException("All CurveIDs in the metadata must be unique.")