import pytest

from app.consistency import WelllogDataConsistencyChecks
from app.model.model_utils import to_record
from app.model.osdu_model import Curve120

from tests.unit.generate_data import generate_df


@pytest.mark.parametrize("columns_count", [
    pytest.param(1024),
    pytest.param(100_000, marks=[pytest.mark.slow, pytest.mark.perf]),
])
def test_welllog_number_column_should_validate_many_columns(welllog120_v3_list, columns_count):
    # GIVEN a record/bulk with more than 255 columns
    welllog_record = welllog120_v3_list[0].copy(deep=True)
    welllog_record.data.Curves = [Curve120(CurveID='C1', NumberOfColumns=columns_count)]

    df = generate_df([f'C1[{i}]' for i in range(columns_count)], [0, 1])

    # THEN check should work and not raise
    record = to_record(welllog_record)
    WelllogDataConsistencyChecks.check_bulk_consistency_on_post_bulk(record, df)
