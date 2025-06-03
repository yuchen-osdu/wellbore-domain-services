import pytest
from pydantic import BaseModel

from app.consistency import WelllogDataConsistencyChecks
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
