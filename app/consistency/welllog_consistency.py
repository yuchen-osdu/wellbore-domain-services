from typing import Dict, Optional
from enum import Enum

import pandas as pd
from dask.dataframe import DataFrame as DaskDataFrame

from odes_storage.models import Record

from app.helper.traces_ot import get_tracer

from app.bulk_persistence import (
    BulkRecordNotFound,
    DaskBulkStorage,
    ConsistencyException,
    DataConsistencyChecks,
    submit_with_trace,
    BulkInfoForConsistency,
    ColumnDescribe,
)
from app.context import get_ctx
from .reference_check import check_reference_is_strictly_monotonic, raise_if_dict_value_is_different
from .unique import get_unique_dict_attr_values
from ..model.entity_utils import get_data_partition_from_record_id

_tracer = get_tracer()


class WellLogProperties(str, Enum):
    CURVES = "Curves"
    CURVE_ID = "CurveID"
    REFERENCE_CURVE_ID = "ReferenceCurveID"
    SAMPLING_START = "SamplingStart"
    SAMPLING_STOP = "SamplingStop"
    LOG_CURVE_FAMILY_ID = "LogCurveFamilyID"
    NUMBER_OF_COLUMNS = "NumberOfColumns"


class DuplicatedCurveIdException(ConsistencyException):
    """raised if all curveID values are not unique"""


class ReferenceCurveIdNotFoundException(ConsistencyException):
    """raised when there is no curve with a curveID value equal to the ReferenceCurveID value"""


class ColumnDoesNotMatchCurveIdException(ConsistencyException):
    """raised when column doesn't match any CurveID"""


class TotalOfColumnsDoesNotMatchFieldNumberOfColumnsException(ConsistencyException):
    """raised when total of columns doesn't match NumberOfColumns field"""


@_tracer.start_as_current_span("welllog_consistency")
def check_welllog_consistency(wl: Record):
    """
    Check wellLog metadata. Curves ids in data.Curves must be unique Welllog must have a curve whose curveID value is
    equal to the  wellLog's ReferenceCurveID value if any
    :param wl: well log object to be verified
    :raise:
        DuplicatedCurveIdException: All CurveIDs are not unique.
        ReferenceCurveIdNotFoundException: No curve whose curveID value are equal to ReferenceCurveID value.
    """
    if not wl.data:
        # There are no Curves or ReferenceCurveID
        return

    curves = wl.data.get(WellLogProperties.CURVES.value) or {}
    reference_curve_id = wl.data.get(WellLogProperties.REFERENCE_CURVE_ID.value)

    # All curve ids must be unique
    curve_ids, duplicated_error = get_unique_dict_attr_values(curves, WellLogProperties.CURVE_ID.value)
    if duplicated_error:
        raise DuplicatedCurveIdException()

    if reference_curve_id and reference_curve_id not in curve_ids:
        raise ReferenceCurveIdNotFoundException()


class WelllogDataConsistencyChecks(DataConsistencyChecks):
    """Check welllog data consistency
    bulk columns and welllog curvesIDs must match.
    welllog referenceCurveID must match a welllog curve
    Reference should be strictly monotonic increasing or strictly monotonic decreasing
    Top & bottom reference values  should match welllog metadata ie:
        SamplingStart is close to top reference value with 1e-9% tolerance
        SamplingStop is close to bottom reference value with 1e-9% tolerance
    """

    @classmethod
    def get_reference_curve(cls, record: Record) -> Optional[str]:
        if not record.data:
            return None
        return record.data.get(WellLogProperties.REFERENCE_CURVE_ID.value)

    @classmethod
    def check_bulk_consistency(cls, record: Record, bulk_info: BulkInfoForConsistency):
        if not record.data:
            return

        cls._check_columns_consistency(record.data, bulk_info.curves)

        reference_name = record.data.get(WellLogProperties.REFERENCE_CURVE_ID.value)
        if reference_name not in bulk_info.curves:
            return

        data_partition = get_data_partition_from_record_id(record)
        if not cls._is_curve_reference_family_measured_depth(record.data, data_partition):
            return

        if bulk_info.reference is not None and reference_name == bulk_info.reference.name:
            cls._check_reference(record, bulk_info.reference)

    @classmethod
    @_tracer.start_as_current_span("bulk_consistency")
    def check_bulk_consistency_on_post_bulk(cls, record: Record, df: pd.DataFrame):
        """Perform welllog consistency checks of a bulk  dataframe against a welllog record used by bulk_persistence
            when post a whole bulk (not chunking apis)
        :param: record (Record): welllog record to check
        :param: df (pandas.DataFrame): bulk data to check against the record
        :raise: ConsistencyException
        """
        if not record.data:
            return

        reference_name = record.data.get(WellLogProperties.REFERENCE_CURVE_ID.value)
        if reference_name not in df.columns:
            reference_name = None

        bulk_info = BulkInfoForConsistency(
            rowCount=len(df.index),
            curves=DataConsistencyChecks._get_curve_name_and_column_count(df.columns),
            reference=ColumnDescribe.from_column(df, reference_name) if reference_name else None,
        )
        cls.check_bulk_consistency(record, bulk_info)

    @classmethod
    @_tracer.start_as_current_span("bulk_consistency")
    async def check_bulk_consistency_on_commit_session(cls, record: Record, bulk_id: str):
        """Perform welllog consistency checks of a bulk  against a welllog record used by bulk_persistence
            when commit a session (chunking apis)
        :param: record (Record): welllog record to check
        :param: bulk_id (str): id of the bulk  to check against the record
        :raise: ConsistencyException
        """

        # check col match record.curves
        dask_blob_storage = await get_ctx().app_injector.get(DaskBulkStorage)
        stats = await dask_blob_storage.read_stat(record.id, bulk_id)
        schema = stats.get("schema")

        curve_sizes = DataConsistencyChecks._get_curve_name_and_column_count(schema.keys())
        cls._check_columns_consistency(record.data, curve_sizes)

        # check reference
        if not record.data:
            return

        reference_curve_id = record.data.get(WellLogProperties.REFERENCE_CURVE_ID.value)
        if not reference_curve_id:
            return

        data_partition = get_data_partition_from_record_id(record)
        if not cls._is_curve_reference_family_measured_depth(record.data, data_partition):
            return

        try:
            ref_ddf, _ = await dask_blob_storage.load_bulk_and_catalog(record.id, bulk_id, columns=[reference_curve_id])
        except BulkRecordNotFound:
            return

        # wrap what should be called in dask workers
        def check_welllog_reference(wl_record: Record, df: DaskDataFrame):
            ref = df[[reference_curve_id]].compute()
            ref_bulk_info = ColumnDescribe.from_column(ref, reference_curve_id)
            cls._check_reference(wl_record, ref_bulk_info)

        await submit_with_trace(dask_blob_storage.client, check_welllog_reference, record, ref_ddf)

    @staticmethod
    def _check_columns_consistency(wl_data: dict, curve_sizes: Dict[str, int]):
        """Checks bulk data column names match welllog record curves ids
        :param: wl_data: welllog data part
        :param: curve_sizes: column's labels with column number
        :raise: ColumnDoesNotMatchCurveIdException: column and record's curves doesn't match
        """

        curves = wl_data.get(WellLogProperties.CURVES)
        if not curves and len(curve_sizes) > 0:
            raise ColumnDoesNotMatchCurveIdException(
                f"Column(s) do(es) not match any {WellLogProperties.CURVE_ID.value} of the WellLog record."
            )

        curve_sizes_from_meta = {
            c[WellLogProperties.CURVE_ID.value]: c.get(WellLogProperties.NUMBER_OF_COLUMNS.value, 1) for c in curves
        }

        not_matching_col_name = curve_sizes.keys() - curve_sizes_from_meta.keys()
        if any(not_matching_col_name):
            raise ColumnDoesNotMatchCurveIdException(
                f"Column(s) {', '.join(not_matching_col_name)} do(es) not match any {WellLogProperties.CURVE_ID.value}"
                f" of the WellLog record."
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
                f" the '{WellLogProperties.NUMBER_OF_COLUMNS.value}' property value in the WellLog record for"
                f" {WellLogProperties.CURVE_ID.value}: {not_matching_nb_col_per_name} ."
            )

    @staticmethod
    def _check_reference(wl: Record, ref_bulk_info: ColumnDescribe):
        check_reference_is_strictly_monotonic(ref_bulk_info)
        raise_if_dict_value_is_different(
            record_data=wl.data,
            attr_name=WellLogProperties.SAMPLING_START.value,
            reference_value=ref_bulk_info.start,
            error_msg=(
                "Reference top value ({reference_value}) is different from {attr_name} value ({attr_value}) of the"
                " WellLog record."
            ),
        )

        raise_if_dict_value_is_different(
            record_data=wl.data,
            attr_name=WellLogProperties.SAMPLING_STOP.value,
            reference_value=ref_bulk_info.end,
            error_msg=(
                "Reference bottom value ({reference_value}) is different from {attr_name} value ({attr_value}) of the"
                " WellLog record."
            ),
        )

    @staticmethod
    def _is_curve_reference_family_measured_depth(data: dict, data_partition: str):
        log_curve_family_id_expected = data_partition + ":reference-data--LogCurveFamily:Measured%20Depth:"
        return any(
            curve.get(WellLogProperties.LOG_CURVE_FAMILY_ID.value, None) == log_curve_family_id_expected
            for curve in data[WellLogProperties.CURVES.value]
            if curve[WellLogProperties.CURVE_ID.value] == data[WellLogProperties.REFERENCE_CURVE_ID.value]
        )
