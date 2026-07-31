import pytest
from pydantic import BaseModel

from app.consistency import WelllogDataConsistencyChecks, ColumnDoesNotMatchCurveIdException
from app.model.model_utils import to_record

from tests.unit.generate_data import generate_df

class Curve(BaseModel):
    CurveID: str | None = None
    NumberOfColumns: int | None = None

@pytest.mark.parametrize("columns_count", [
    pytest.param(1024),
    pytest.param(100_000, marks=[pytest.mark.slow, pytest.mark.perf]),
])
def test_welllog_number_column_should_validate_many_columns(welllog120_v3_record_list, columns_count):
    # GIVEN a record/bulk with more than 255 columns
    welllog_record = welllog120_v3_record_list[0].model_copy(deep=True)
    welllog_record.data['Curves'] = [Curve(CurveID='C1', NumberOfColumns=columns_count)]

    df = generate_df([f'C1[{i}]' for i in range(columns_count)], [0, 1])

    # THEN check should work and not raise
    record = to_record(welllog_record)
    WelllogDataConsistencyChecks.check_bulk_consistency_on_post_bulk(record, df)


def test_welllog_curve_without_curveid_raises_consistency_error(welllog120_v3_record_list):
    # GIVEN a WellLog record whose Curves contain an entry missing CurveID
    welllog_record = welllog120_v3_record_list[0].model_copy(deep=True)
    welllog_record.data['Curves'] = [Curve(CurveID='C1', NumberOfColumns=1), Curve(NumberOfColumns=1)]

    df = generate_df(['C1'], [0, 1])

    record = to_record(welllog_record)

    # THEN a consistency (client) error is raised instead of an unhandled KeyError surfacing as HTTP 500
    with pytest.raises(ColumnDoesNotMatchCurveIdException):
        WelllogDataConsistencyChecks.check_bulk_consistency_on_post_bulk(record, df)
