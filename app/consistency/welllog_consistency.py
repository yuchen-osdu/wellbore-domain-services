import math
import re
from typing import Iterable, Set

import pandas as pd
from app.bulk_persistence.consistency_checks import ConsistencyException, DataConsistencyChecks
from app.bulk_persistence.dask.dask_bulk_storage import DaskBulkStorage
from app.bulk_persistence.dask.traces import submit_with_trace
from app.model.model_utils import from_record
from app.model.osdu_model import WellLog110
from app.utils import get_ctx
from dask.dataframe.core import DataFrame as DaskDataFrame
from odes_storage.models import Record

from .unique import get_unique_ids


class DuplicatedCurveIdException(ConsistencyException):
    """raised if all curveID values are not unique"""


class ReferenceCurveIdNotFoundException(ConsistencyException):
    """raised when there is no curve with a curveID value equal to the ReferenceCurveID value"""


class ColumnDoesNotMatchCurveIdException(ConsistencyException):
    """raised when column doesn't match any CurveID"""


class ReferenceCurveException(ConsistencyException):
    """raised when column doesn't match any CurveID"""


def check_welllog_consistency(wl: WellLog110):
    """Check wellLog metadata.

    Each curves in data.Curves must have a unique CurveID.
    Welllog must have a curve whose curveID value is equal to the  wellLog's ReferenceCurveID value

    Args:
        wl (Welllog): wellLog object to be verified

    Returns:

    Raises:
        DuplicatedCurveIdException: All CurveIDs are not unique.
        ReferenceCurveIdNotFoundException: No curve whose curveID value are equal to ReferenceCurveID value.
    """

    if not wl.data:
        return

    if wl.data.ReferenceCurveID and not wl.data.Curves:
        raise ReferenceCurveIdNotFoundException()

    curve_ids, duplicated_error = get_unique_ids(wl.data.Curves, "CurveID")

    if duplicated_error:
        raise DuplicatedCurveIdException()
    # Check there is a curve with curveID == referenceCurveID
    if wl.data.ReferenceCurveID and wl.data.ReferenceCurveID not in curve_ids:
        raise ReferenceCurveIdNotFoundException()


class WelllogDataConsistencyChecks(DataConsistencyChecks):
    """Check welllog data consistency
    bulk columns and welllog curvesIDs must match.
    welllog referenceCurveID must match a welllog curve
    Reference should be strictly monotonic increasing or strictly monotonic decresing
    Reference top & bottom values should match welllog metadata.
    """

    @classmethod
    def check_bulk_consistency_on_post_bulk(cls, record: Record, df: pd.DataFrame):
        wl = from_record(WellLog110, record)
        cls._check_columns_consistency(wl, df.columns)

        if not (wl.data and wl.data.ReferenceCurveID):
            return

        ref = df[wl.data.ReferenceCurveID]

        cls._check_reference_is_strictly_monotonic(ref)
        cls._check_top_bottom_reference(wl, ref)

    @classmethod
    async def check_bulk_consistency_on_commit_session(cls, record: Record, new_bulk_id):
        wl = from_record(WellLog110, record)

        # check col match record.curves
        dask_blob_storage = await get_ctx().app_injector.get(DaskBulkStorage)
        stats = await dask_blob_storage.read_stat(record.id, new_bulk_id)
        schema = stats.get("schema")

        cls._check_columns_consistency(wl, schema.keys())

        # check reference
        if not (wl.data and wl.data.ReferenceCurveID):
            return

        ref_ddf = await dask_blob_storage.load_bulk(record.id, new_bulk_id, columns=[wl.data.ReferenceCurveID])

        # wrap what should be called in dask workers
        def check_welllog_reference(wl: WellLog110, ref_ddf: DaskDataFrame):
            ref = ref_ddf[wl.data.ReferenceCurveID].compute()
            cls._check_reference_is_strictly_monotonic(ref)
            cls._check_top_bottom_reference(wl, ref)

        await submit_with_trace(dask_blob_storage.client, check_welllog_reference, wl, ref_ddf)

    @staticmethod
    def _check_columns_consistency(wl: WellLog110, cols: Iterable[str]):

        """Check if col_names match curveID in bulk data

        Args:
            wl(welllog): welllog record to check
            df(pandas.DataFrame): the bulk data

        Returns: None

        Raises:
            ColumnDoesNotMatchCurveIdException: a column doesn't match any CurveID
        """
        if (not wl.data or not wl.data.Curves) and len(cols) > 0:
            raise ColumnDoesNotMatchCurveIdException(f"Columns doesn't match any CurveID")

        curve_ids, _ = get_unique_ids(wl.data.Curves, "CurveID")
        col_names = WelllogDataConsistencyChecks._get_data_columns_name(cols)

        not_matching_col_name = [col_name for col_name in col_names if col_name not in curve_ids]
        if any(not_matching_col_name):
            raise ColumnDoesNotMatchCurveIdException(
                f"Column(s) {','.join(not_matching_col_name)} doesn't match any CurveID"
            )

    @staticmethod
    def _get_data_columns_name(cols: Iterable[str]) -> Set[str]:
        def get_name(txt):
            re_array_selection = re.compile(r"^(?P<name>.+)\[(?P<start>[^:]+):?(?P<stop>.*)\]$")
            match = re_array_selection.match(txt)
            if not match:
                return txt
            return match["name"]

        res = (get_name(col) for col in cols if col != "")
        return {r for r in res if r != ""}

    @staticmethod
    def _check_reference_is_strictly_monotonic(ref):
        # is_monotonic_increasing & is_monotonic_decreasing is not strict so we need to check unique values before
        if ref.duplicated().any():
            raise ReferenceCurveException("Reference curve must have only unique values")

        if not ref.is_monotonic_increasing and not ref.is_monotonic_decreasing:
            # Check Nan values are not allowed
            if ref.isnull().values.any():
                raise ReferenceCurveException("Nan values in reference curve is not allowed")
            else:
                raise ReferenceCurveException("Reference must be monotonically increasing or decreasing")

    @staticmethod
    def _check_top_bottom_reference(wl: WellLog110, ref):
        def raise_if_attr_value_is_different(attr_name: str, value):
            current_value = getattr(wl.data, attr_name, None)
            if current_value is not None and not math.isclose(current_value, value):
                raise ReferenceCurveException(
                    f"Reference {attr_name} value ({value}) is not egal to welllog's {attr_name} value ({current_value})"
                )

        raise_if_attr_value_is_different("TopMeasuredDepth", ref.iloc[0])
        raise_if_attr_value_is_different("SamplingStart", ref.iloc[0])
        raise_if_attr_value_is_different("BottomMeasuredDepth", ref.iloc[-1])
        raise_if_attr_value_is_different("SamplingStop", ref.iloc[-1])
