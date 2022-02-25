import math
import re
from typing import Iterable, Set

import pandas as pd
from app.helper.traces import with_trace
from app.bulk_persistence.consistency_checks import ConsistencyException, DataConsistencyChecks
from app.bulk_persistence.dask.dask_bulk_storage import DaskBulkStorage
from app.bulk_persistence.dask.traces import submit_with_trace
from app.model.model_utils import from_record
from app.model.osdu_model import WellLog110
from app.utils import get_ctx
from dask.dataframe.core import DataFrame as DaskDataFrame
from odes_storage.models import Record

from .unique import get_unique_attr_values


class DuplicatedCurveIdException(ConsistencyException):
    """raised if all curveID values are not unique"""


class ReferenceCurveIdNotFoundException(ConsistencyException):
    """raised when there is no curve with a curveID value equal to the ReferenceCurveID value"""


class ColumnDoesNotMatchCurveIdException(ConsistencyException):
    """raised when column doesn't match any CurveID"""


class ReferenceCurveException(ConsistencyException):
    """raised when column doesn't match any CurveID"""


@with_trace('welllog_consistency')
def check_welllog_consistency(wl: WellLog110):
    """Check wellLog metadata.

    Curves ids in data.Curves must be unique
    Welllog must have a curve whose curveID value is equal to the  wellLog's ReferenceCurveID value if any

    Args:
        wl (WellLog110): wellLog object to be verified

    Returns:
        None

    Raises:
        DuplicatedCurveIdException: All CurveIDs are not unique.
        ReferenceCurveIdNotFoundException: No curve whose curveID value are equal to ReferenceCurveID value.
    """

    # There are no Curves or ReferenceCurveID
    if not wl.data:
        return

    if not wl.data.Curves and not wl.data.ReferenceCurveID:
        return

    # Can't define a  ReferenceCurveID fi wellbore doesn't have any Curve
    if not wl.data.Curves and wl.data.ReferenceCurveID:
        raise ReferenceCurveIdNotFoundException()

    # All curve ids must be unique
    curve_ids, duplicated_error = get_unique_attr_values(wl.data.Curves, "CurveID")
    if duplicated_error:
        raise DuplicatedCurveIdException()

    # ReferenceCurveID should match a curve
    if wl.data.ReferenceCurveID and wl.data.ReferenceCurveID not in curve_ids:
        raise ReferenceCurveIdNotFoundException()


class WelllogDataConsistencyChecks(DataConsistencyChecks):
    """Check welllog data consistency
    bulk columns and welllog curvesIDs must match.
    welllog referenceCurveID must match a welllog curve
    Reference should be strictly monotonic increasing or strictly monotonic decreasing
    Top & bottom reference values  should match welllog ie:
        top == TopMeasuredDepth == SamplingStart AND bottom == BottomMeasuredDepth == SamplingStop
    """

    # regular expression pattern for extracting column name from bulk data column label
    _col_label_pattern = re.compile(r"^(?P<name>.+)\[(?P<start>[^:]+):?(?P<stop>.*)\]$")

    @classmethod
    @with_trace('bulk_consistency')
    def check_bulk_consistency_on_post_bulk(cls, record: Record, df: pd.DataFrame):
        """ Perform welllog consistency checks of a bulk  dataframe against a welllog record
        used by bulk_persistence when post a whole bulk (not chunking apis)

         Args:
            record (Record): welllog record to check
            df (pandas.DataFrame): bulk data to check against the record

        Raises: ConsistencyException

        Returns: None
        """
        wl = from_record(WellLog110, record)
        cls._check_columns_consistency(wl, df.columns)

        if not (wl.data and wl.data.ReferenceCurveID):
            return

        ref = df[wl.data.ReferenceCurveID]

        cls._check_reference_is_strictly_monotonic(ref)
        cls._check_top_bottom_reference(wl, ref)

    @classmethod
    @with_trace('bulk_consistency')
    async def check_bulk_consistency_on_commit_session(cls, record: Record, bulk_id: str):
        """ Perform welllog consistency checks of a bulk  against a welllog record
        used by bulk_persistence when commit a session (chunking apis)

         Args:
            record (Record): welllog record to check
            bulk_id (str): id of the bulk  to check against the record

        Raises: ConsistencyException

        Returns: None
        """
        wl = from_record(WellLog110, record)

        # check col match record.curves
        dask_blob_storage = await get_ctx().app_injector.get(DaskBulkStorage)
        stats = await dask_blob_storage.read_stat(record.id, bulk_id)
        schema = stats.get("schema")

        cls._check_columns_consistency(wl, schema.keys())

        # check reference
        if not (wl.data and wl.data.ReferenceCurveID):
            return

        ref_ddf = await dask_blob_storage.load_bulk(record.id, bulk_id, columns=[wl.data.ReferenceCurveID])

        # wrap what should be called in dask workers
        def check_welllog_reference(wl: WellLog110, ref_ddf: DaskDataFrame):
            ref = ref_ddf[wl.data.ReferenceCurveID].compute()
            cls._check_reference_is_strictly_monotonic(ref)
            cls._check_top_bottom_reference(wl, ref)

        await submit_with_trace(dask_blob_storage.client, check_welllog_reference, wl, ref_ddf)

    @staticmethod
    def _check_columns_consistency(wl: WellLog110, col_labels: Iterable[str]):
        """Checks bulk data column names match welllog record curves ids

        Args:
            wl(WellLog110): welllog record
            col_labels: column's labels to check against the record

        Returns: None

        Raises:
            ColumnDoesNotMatchCurveIdException: column and record's curves doesn't match
        """
        if (not wl.data or not wl.data.Curves) and len(col_labels) > 0:
            raise ColumnDoesNotMatchCurveIdException(f"Columns doesn't match any CurveID of the WellLog record.")

        curve_ids, _ = get_unique_attr_values(wl.data.Curves, "CurveID")
        col_names = WelllogDataConsistencyChecks._get_data_columns_name(col_labels)

        not_matching_col_name = [col_name for col_name in col_names if col_name not in curve_ids]
        if any(not_matching_col_name):
            raise ColumnDoesNotMatchCurveIdException(
                f"Column(s) {','.join(not_matching_col_name)} doesn't match any CurveID of the WellLog record."
            )

    @staticmethod
    def _get_data_columns_name(col_labels: Iterable[str]) -> Set[str]:
        """
        Get column names from bulk data column labels
        """
        def _get_col_name_from_col_label(col_label: str):
            match = WelllogDataConsistencyChecks._col_label_pattern.match(col_label)
            if not match:
                return col_label
            return match["name"]

        res = (_get_col_name_from_col_label(col) for col in col_labels if col)
        return {r for r in res if r != ""}

    @staticmethod
    def _check_reference_is_strictly_monotonic(ref: pd.Series):
        # check unique values because is_monotonic_increasing & is_monotonic_decreasing are not strict
        if ref.duplicated().any():
            raise ReferenceCurveException("Repeated values in a reference curve aren't allowed.")

        if not ref.is_monotonic_increasing and not ref.is_monotonic_decreasing:
            # Nan values
            if ref.isnull().values.any():
                raise ReferenceCurveException("Nan values in a reference curve are not allowed.")
            else:
                raise ReferenceCurveException("Reference must be monotonically increasing or decreasing.")

    @staticmethod
    def _check_top_bottom_reference(wl: WellLog110, ref: pd.Series):
        def raise_if_attr_value_is_different(attr_name: str, value):
            current_value = getattr(wl.data, attr_name, None)
            if current_value is not None and not math.isclose(current_value, value):
                raise ReferenceCurveException(
                    f"Reference {attr_name} value ({value}) is different from {attr_name} value ({current_value}) of the WellLog record."
                )

        raise_if_attr_value_is_different("TopMeasuredDepth", ref.iloc[0])
        raise_if_attr_value_is_different("SamplingStart", ref.iloc[0])
        raise_if_attr_value_is_different("BottomMeasuredDepth", ref.iloc[-1])
        raise_if_attr_value_is_different("SamplingStop", ref.iloc[-1])
