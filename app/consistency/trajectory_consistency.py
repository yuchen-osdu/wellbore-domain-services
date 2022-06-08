import pandas as pd
from dask.dataframe.core import DataFrame as DaskDataFrame
from typing import List
import math

from odes_storage.models import Record

from app.model.osdu_model import WellboreTrajectory110
from app.helper.traces import with_trace
from app.bulk_persistence import ConsistencyException, DataConsistencyChecks, \
	BulkRecordNotFound, \
	DaskBulkStorage, submit_with_trace
from app.model.model_utils import from_record
from app.context import get_ctx

from .unique import get_unique_attr_values
from .reference_check import check_reference_is_strictly_monotonic, raise_if_attr_value_is_different


class DuplicatedStationProperties(RuntimeError):
    """raised if all trajectoryStationProperties names are not unique"""


class ColumnDoesNotMatchTrajectoryStationException(ConsistencyException):
    """raised when column doesn't match any AvailableTrajectoryStationProperties"""


def check_trajectory_consistency(traj: WellboreTrajectory110):
    """Check if trajectory is consistent.

    Each station in data.AvailableTrajectoryStationProperties must have a unique name.

    Args:
        traj (WellboreTrajectory110): trajectory object to be verified

    Returns:

    Raises:
        DuplicatedStationProperties: All AvailableTrajectoryStationProperties Name  are not unique.
    """
    if not traj.data or not traj.data.AvailableTrajectoryStationProperties:
        return

    # All   name  must be unique
    station_name, duplicated_error = get_unique_attr_values(
        traj.data.AvailableTrajectoryStationProperties,
        "Name"
    )
    if duplicated_error:
        raise DuplicatedStationProperties()


class TrajectoryDataConsistencyChecks(DataConsistencyChecks):
    """Check welllogTrajectory data consistency
    bulk columns and TrajectoryStationProperty names must match.
    MD column should be strictly monotonic increasing or strictly monotonic decreasing
    MD Top & bottom values  should match WelllogTrajectory
    """

    reference_trajectory_station_property_type_id = ":reference-data--TrajectoryStationPropertyType:MD:"

    @staticmethod
    def get_reference_name(traj: WellboreTrajectory110):
        if not traj.data.AvailableTrajectoryStationProperties:
            return None
        for station in traj.data.AvailableTrajectoryStationProperties:
            if station and hasattr(station, "TrajectoryStationPropertyTypeID"):
                if (
                    station.TrajectoryStationPropertyTypeID
                    and TrajectoryDataConsistencyChecks.reference_trajectory_station_property_type_id
                    in station.TrajectoryStationPropertyTypeID
                ):
                    if hasattr(station, "Name") and station.Name:
                        return station.Name
        return None

    @classmethod
    @with_trace("bulk_consistency")
    def check_bulk_consistency_on_post_bulk(cls, record: Record, df: pd.DataFrame):
        """Perform trajectory consistency checks of a bulk  dataframe against welllogTrajectory record
        Called  when post a whole bulk (not chunking apis)

         Args:
            record (Record): WelllogTrajectory record to check
            df (pandas.DataFrame): bulk data to check against the record

        Raises: ConsistencyException

        Returns: None
        """
        if not record.data:
            return

        traj = from_record(WellboreTrajectory110, record)
        cls._check_columns_consistency(traj, df.columns)

        reference_name = TrajectoryDataConsistencyChecks.get_reference_name(traj)
        if not reference_name:
            return

        if reference_name in df:
            ref = df[reference_name]
            check_reference_is_strictly_monotonic(ref)
            cls._check_top_bottom_reference(traj, ref)

    @classmethod
    @with_trace("bulk_consistency")
    async def check_bulk_consistency_on_commit_session(cls, record: Record, bulk_id: str):
        traj = from_record(WellboreTrajectory110, record)

        # check colums match TrajectoryStationProperties names
        dask_blob_storage = await get_ctx().app_injector.get(DaskBulkStorage)
        stats = await dask_blob_storage.read_stat(record.id, bulk_id)
        schema = stats.get("schema")

        cls._check_columns_consistency(traj, schema.keys())

        reference_name = TrajectoryDataConsistencyChecks.get_reference_name(traj)
        if not reference_name:
            return

        try:
            ref_ddf = await dask_blob_storage.load_bulk(record.id, bulk_id, columns=[reference_name])
        except BulkRecordNotFound:
            return

        # wrap what should be called in dask workers
        def check_reference(traj: WellboreTrajectory110, ref_ddf_: DaskDataFrame):
            ref = ref_ddf_[reference_name].compute()
            check_reference_is_strictly_monotonic(ref)
            cls._check_top_bottom_reference(traj, ref)

        await submit_with_trace(dask_blob_storage.client, check_reference, traj, ref_ddf)

    @staticmethod
    def _check_columns_consistency(traj: WellboreTrajectory110, col_labels: List[str]):
        error_msg = "do(es) not match any AvailableTrajectoryStationProperties name in the WellboreTrajectory record."

        curve_ids, _ = get_unique_attr_values(traj.data.AvailableTrajectoryStationProperties, "Name")
        col_names = DataConsistencyChecks._get_name_and_count_data_columns(col_labels).keys()

        not_matching_col_name = [col_name for col_name in col_names if col_name not in curve_ids]
        if any(not_matching_col_name):
            raise ColumnDoesNotMatchTrajectoryStationException(
                f"Column(s) {', '.join(not_matching_col_name)} {error_msg}"
            )

    @staticmethod
    def _check_top_bottom_reference(traj: WellboreTrajectory110, ref: pd.Series):
        raise_if_attr_value_is_different(
            record_data=traj.data,
            attr_name="TopDepthMeasuredDepth",
            reference_value=ref.iloc[0],
            error_msg="First value ({reference_value}) of the measured depth is different from {attr_name} value ({attr_value}) of the WellboreTrajectory record."

        )

        raise_if_attr_value_is_different(
            record_data=traj.data,
            attr_name="BaseDepthMeasuredDepth",
            reference_value=ref.iloc[-1],
            error_msg="Last value ({reference_value}) of the measured depth is different from {attr_name} value ({attr_value}) of the WellboreTrajectory record."
        )



