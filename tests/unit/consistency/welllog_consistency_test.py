from app.consistency import WelllogDataConsistencyChecks
from app.model.osdu_model import Curve120

from tests.unit.generate_data import generate_df


def test_welllog_number_column_should_validate_many_columns(welllog120_v3_list):
    # GIVEN a record/bulk with more than 255 columns (5000 here)
    welllog_record = welllog120_v3_list[0].copy(deep=True)
    welllog_record.data.Curves = [Curve120(CurveID='C1', NumberOfColumns=5000)]

    df = generate_df([f'C1[{i}]' for i in range(5000)], [0, 1])

    # THEN check should work and not raise
    WelllogDataConsistencyChecks.check_bulk_consistency_on_post_bulk(welllog_record, df)
