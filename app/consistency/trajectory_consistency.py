from typing import Dict

import pandas as pd
from dask.dataframe.core import DataFrame as DaskDataFrame

from odes_storage.models import Record
from app.helper.traces import with_trace
from app.bulk_persistence import (
    ConsistencyException,
    DataConsistencyChecks,
    BulkRecordNotFound,
    DaskBulkStorage,
    submit_with_trace,
    ColumnDescribe,
    BulkInfoForConsistency,
)

from app.context import get_ctx

from .unique import get_unique_dict_attr_values
from .reference_check import check_reference_is_strictly_monotonic, raise_if_dict_value_is_different

AVAILABLE_TRAJECTORY_STATION_PROPERTIES_KEY = "AvailableTrajectoryStationProperties"
TRAJECTORY_STATION_PROPERTY_TYPE_ID = "TrajectoryStationPropertyTypeID"


class DuplicatedStationProperties(RuntimeError):
    """raised if all trajectoryStationProperties names are not unique"""


class ColumnDoesNotMatchTrajectoryStationException(ConsistencyException):
    """raised when column doesn't match any AvailableTrajectoryStationProperties"""


def check_trajectory_consistency(trajectory: Record):
    """Check if trajectory meta data are consistent.

    Each station in data.AvailableTrajectoryStationProperties must have a unique name.

    Args:
        trajectory (WellboreTrajectory110): trajectory object to be verified

    Returns:

    Raises:
        DuplicatedStationProperties: All AvailableTrajectoryStationProperties Name  are not unique.
    """
    if not trajectory.data:
        return
    if AVAILABLE_TRAJECTORY_STATION_PROPERTIES_KEY not in trajectory.data:
        return

    # All   name  must be unique
    station_name, duplicated_error = get_unique_dict_attr_values(
        trajectory.data[AVAILABLE_TRAJECTORY_STATION_PROPERTIES_KEY], "Name"
    )
    if duplicated_error:
        raise DuplicatedStationProperties()


class TrajectoryDataConsistencyChecks(DataConsistencyChecks):
    """Check welllogTrajectory bulk data consistency compared to info inside the metadata
    bulk columns and TrajectoryStationProperty names must match.
    MD column should be strictly monotonic increasing or strictly monotonic decreasing
    MD Top & bottom values  should match WelllogTrajectory
    """

    reference_trajectory_station_property_type_id = ":reference-data--TrajectoryStationPropertyType:MD:"

    @classmethod
    def check_bulk_consistency(cls, record: Record, bulk_info: BulkInfoForConsistency):
        if not record.data:
            return

        cls._check_columns_consistency(record.data, bulk_info.curves)

        reference_name = cls._get_reference_name(record.data)
        if not reference_name:
            return

        if bulk_info.reference is not None and reference_name == bulk_info.reference.name:
            cls._check_reference(record, bulk_info.reference)

    @staticmethod
    def _get_reference_name(record_data: Dict):
        station_properties = record_data.get(AVAILABLE_TRAJECTORY_STATION_PROPERTIES_KEY)
        if station_properties is None:
            return None
        for station in station_properties:
            if station and TRAJECTORY_STATION_PROPERTY_TYPE_ID in station:
                if (
                    station[TRAJECTORY_STATION_PROPERTY_TYPE_ID]
                    and TrajectoryDataConsistencyChecks.reference_trajectory_station_property_type_id
                    in station[TRAJECTORY_STATION_PROPERTY_TYPE_ID]
                ):
                    if "Name" in station and station["Name"]:
                        return station["Name"]
        return None

    @classmethod
    @with_trace("bulk_consistency")
    def check_bulk_consistency_on_post_bulk(cls, record: Record, df: pd.DataFrame):
        """Perform record consistency checks of a bulk  dataframe against welllogTrajectory record called
            when post a whole bulk (not chunking apis)
        :param: record (Record): WelllogTrajectory record to check
        :param: df (pandas.DataFrame): bulk data to check against the record
        :raise: ConsistencyException
        """
        if not record.data:
            return

        reference_name = TrajectoryDataConsistencyChecks._get_reference_name(record.data)
        if reference_name not in df.columns:
            reference_name = None

        bulk_info = BulkInfoForConsistency.construct(
            rowCount=len(df.index),
            curves=DataConsistencyChecks._get_curve_name_and_column_count(df.columns),
            reference=ColumnDescribe.from_column(df, reference_name) if reference_name else None,
        )
        cls.check_bulk_consistency(record, bulk_info)

    @classmethod
    @with_trace("bulk_consistency")
    async def check_bulk_consistency_on_commit_session(cls, record: Record, bulk_id: str):
        # check columns match TrajectoryStationProperties names
        dask_blob_storage = await get_ctx().app_injector.get(DaskBulkStorage)
        stats = await dask_blob_storage.read_stat(record.id, bulk_id)
        schema = stats.get("schema")

        curve_sizes = DataConsistencyChecks._get_curve_name_and_column_count(schema.keys())
        cls._check_columns_consistency(record.data, curve_sizes)

        reference_name = TrajectoryDataConsistencyChecks._get_reference_name(record.data)
        if not reference_name:
            return

        try:
            ref_ddf, _ = await dask_blob_storage.load_bulk_and_catalog(record.id, bulk_id, columns=[reference_name])
        except BulkRecordNotFound:
            return

        # wrap what should be called in dask workers
        def check_reference(record: Record, ref_ddf_: DaskDataFrame):
            ref = ref_ddf_[[reference_name]].compute()
            ref_bulk_info = ColumnDescribe.from_column(ref, reference_name)
            cls._check_reference(record, ref_bulk_info)

        await submit_with_trace(dask_blob_storage.client, check_reference, record, ref_ddf)

    @staticmethod
    def _check_columns_consistency(record_data: dict, curve_sizes: Dict[str, int]):
        error_msg = "do(es) not match any AvailableTrajectoryStationProperties name in the WellboreTrajectory record."

        curve_ids, _ = get_unique_dict_attr_values(record_data[AVAILABLE_TRAJECTORY_STATION_PROPERTIES_KEY], "Name")

        not_matching_col_name = [col_name for col_name in curve_sizes if col_name not in curve_ids]
        if any(not_matching_col_name):
            raise ColumnDoesNotMatchTrajectoryStationException(
                f"Column(s) {', '.join(not_matching_col_name)} {error_msg}"
            )

    @staticmethod
    def _check_reference(record: Record, ref_bulk_info: ColumnDescribe):
        check_reference_is_strictly_monotonic(ref_bulk_info)
        raise_if_dict_value_is_different(
            record_data=record.data,
            attr_name="TopDepthMeasuredDepth",
            reference_value=ref_bulk_info.start,
            error_msg=(
                "First value ({reference_value}) of the measured depth is different from {attr_name} value"
                " ({attr_value}) of the WellboreTrajectory record."
            ),
        )

        raise_if_dict_value_is_different(
            record_data=record.data,
            attr_name="BaseDepthMeasuredDepth",
            reference_value=ref_bulk_info.end,
            error_msg=(
                "Last value ({reference_value}) of the measured depth is different from {attr_name} value"
                " ({attr_value}) of the WellboreTrajectory record."
            ),
        )
