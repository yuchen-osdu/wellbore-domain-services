from enum import Enum
from typing import Optional, Dict

import pandas as pd
from odes_storage.models import Record

from app.bulk_persistence import DataConsistencyChecks, BulkInfoForConsistency, ConsistencyException
from app.consistency.unique import get_unique_dict_attr_values
from app.context import get_ctx
from app.helper.traces_ot import get_tracer

_tracer = get_tracer()


class WellPressureTestRawMeasurementProperties(str, Enum):
    CURVES = "Curves"
    CURVE_ID = "CurveID"
    NUMBER_OF_COLUMNS = "NumberOfColumns"


class DuplicatedCurveIdException(ConsistencyException):
    """raised if all curveID values are not unique"""


class ColumnDoesNotMatchCurveIdException(ConsistencyException):
    """raised when column doesn't match any CurveID"""


class TotalOfColumnsDoesNotMatchFieldNumberOfColumnsException(ConsistencyException):
    """raised when total of columns doesn't match NumberOfColumns field"""


@_tracer.start_as_current_span("wellpressuretestrawmeasurement_consistency")
def check_well_pressure_test_raw_measurement_consistency(well_pressure_test_raw_measurement_data: Record):
    if not well_pressure_test_raw_measurement_data.data:
        # No Data to check
        return

    curves = well_pressure_test_raw_measurement_data.data.get("Curves", [])

    _, duplicated_error = get_unique_dict_attr_values(curves, "CurveID")
    if duplicated_error:
        raise DuplicatedCurveIdException("All CurveIDs in the metadata must be unique.")


class WellPressureTestRawMeasurementConsistencyChecks(DataConsistencyChecks):
    @classmethod
    def get_reference_curve(cls, record: Record) -> Optional[str]:
        pass

    @classmethod
    def check_bulk_consistency(cls, record: Record, bulk_info: BulkInfoForConsistency):
        if not record.data:
            return

        cls._check_columns_consistency(record.data, bulk_info.curves)

    @classmethod
    @_tracer.start_as_current_span("bulk_consistency")
    def check_bulk_consistency_on_post_bulk(cls, record: Record, df: pd.DataFrame):
        if not record.data:
            return

        bulk_info = BulkInfoForConsistency(
            rowCount=len(df.index),
            curves=DataConsistencyChecks._get_curve_name_and_column_count(df.columns),
        )
        cls.check_bulk_consistency(record, bulk_info)

    @staticmethod
    def _check_columns_consistency(wellpressuretestrawmeasurement_data: dict, curve_sizes: Dict[str, int]):
        """
        Validates the consistency between the column names in bulk data and the curve IDs in the WellPressureTestRawMeasurement metadata.
        Args:
            wellpressuretestrawmeasurement_data (dict): The metadata of the WellPressureTestRawMeasurement containing curve information.
            curve_sizes (Dict[str, int]): A dictionary mapping column names to their respective number of columns.

        Raises:
            ColumnDoesNotMatchCurveIdException: If a column name in `curve_sizes` does not match any CurveID in the metadata
                or if there are no curves in the metadata but `curve_sizes` contains columns.
        """

        curves = wellpressuretestrawmeasurement_data.get(WellPressureTestRawMeasurementProperties.CURVES.value)
        if not curves and len(curve_sizes) > 0:
            raise ColumnDoesNotMatchCurveIdException(
                f"Column(s) do(es) not match any {WellPressureTestRawMeasurementProperties.CURVE_ID.value} of the WellPressureTestRawMeasurement record."
            )

        curve_sizes_from_meta = {
            c[WellPressureTestRawMeasurementProperties.CURVE_ID.value]: c.get(
                WellPressureTestRawMeasurementProperties.NUMBER_OF_COLUMNS.value, 1) for c in curves
        }

        not_matching_col_name = curve_sizes.keys() - curve_sizes_from_meta.keys()
        if any(not_matching_col_name):
            raise ColumnDoesNotMatchCurveIdException(
                f"Column(s) {', '.join(not_matching_col_name)} do(es) not match any {WellPressureTestRawMeasurementProperties.CURVE_ID.value}"
                f" of the WellPressureTestRawMeasurement record."
            )

        not_matching_nb_col_per_name = {
            c: size_in_meta
            for c, size_in_meta in curve_sizes_from_meta.items()
            if c in curve_sizes and curve_sizes[c] != size_in_meta
        }
        if any(not_matching_nb_col_per_name):
            expected_nb_of_col_per_name = {curve_id: curve_sizes[curve_id] for curve_id in not_matching_nb_col_per_name}

            raise TotalOfColumnsDoesNotMatchFieldNumberOfColumnsException(
                f"The number of columns for curve(s): {expected_nb_of_col_per_name} in the bulk data do(es) not match"
                f" the '{WellPressureTestRawMeasurementProperties.NUMBER_OF_COLUMNS.value}' property value in the WellPressureTestRawMesaurement record for"
                f" {WellPressureTestRawMeasurementProperties.CURVE_ID.value}: {not_matching_nb_col_per_name} ."
            )
