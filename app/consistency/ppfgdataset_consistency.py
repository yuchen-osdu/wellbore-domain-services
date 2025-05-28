# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from enum import Enum
from typing import Dict, Optional

import pandas as pd
from odes_storage.models import Record

from app.bulk_persistence import (
    ConsistencyException,
    DataConsistencyChecks,
    BulkInfoForConsistency,
    ColumnDescribe,
)
from app.helper.traces_ot import get_tracer
from .unique import get_unique_dict_attr_values

_tracer = get_tracer()
DEFAULT_NUMBER_OF_COLUMNS = 1

class PPFgDataSetProperties(str, Enum):
    CONTEXT_TYPE_ID = "ContextTypeID"
    REFERENCE_WELL_TRAJECTORY_ID = "ReferenceWellTrajectoryID"
    PRIMARY_REFERENCE_CURVE_ID = "PrimaryReferenceCurveID"
    CURVES = "Curves"
    CURVE_ID = "CurveID"

class DuplicatedCurveIdException(ConsistencyException):
    """raised if all curveID values are not unique"""


class PrimaryReferenceCurveIdNotFoundException(ConsistencyException):
    """raised when there is no curve with a curveID value equal to the PrimaryReferenceCurveId value"""


class ContextTypeIdMissingException(ConsistencyException):
    """raised when there is no value provided for ContextTypeId field."""


class ReferenceWellTrajectoryIdMissingException(ConsistencyException):
    """raised when there is no value provided for ReferenceWellTrajectoryID field."""


class ColumnDoesNotMatchCurveIdException(ConsistencyException):
    """raised when column doesn't match any CurveID"""


@_tracer.start_as_current_span("ppfgdataset_consistency")
def check_ppfgdataset_consistency(ppfgdata: Record):
    """
    Check ppfgdataset metadata
    :param ppfgdata: ppfgdataset object to be verified
    :raise:
        DuplicatedCurveIdException: Raised if all CurveID values in the dataset are not unique.
        PrimaryReferenceCurveIdNotFoundException: Raised when no curve with a CurveID value equal to the PrimaryReferenceCurveId is found.
        ContextTypeIdMissingException: Raised when the ContextTypeId field is missing in the dataset.
        ReferenceWellTrajectoryIdMissingException: Raised when the ReferenceWellTrajectoryID field is missing in the dataset.
    """
    if not ppfgdata.data:
        # There are no Curves or ReferenceCurveID
        return

    # ContextTypeId field needs to be populated
    if not ppfgdata.data.get(PPFgDataSetProperties.CONTEXT_TYPE_ID.value):
        raise ContextTypeIdMissingException()

    # ReferenceWellTrajectoryId field needs to be populated
    if not ppfgdata.data.get(PPFgDataSetProperties.REFERENCE_WELL_TRAJECTORY_ID.value):
        raise ReferenceWellTrajectoryIdMissingException()

    curves = ppfgdata.data.get(PPFgDataSetProperties.CURVES.value, [])
    primary_reference_curve_id = ppfgdata.data.get(PPFgDataSetProperties.PRIMARY_REFERENCE_CURVE_ID.value)

    # All curve ids must be unique
    curve_ids, duplicated_error = get_unique_dict_attr_values(curves, PPFgDataSetProperties.CURVE_ID.value)
    if duplicated_error:
        raise DuplicatedCurveIdException()

    # primary reference curve needs to be present in curves
    if primary_reference_curve_id and primary_reference_curve_id not in curve_ids:
        raise PrimaryReferenceCurveIdNotFoundException()


class PPFGDatasetConsistencyChecks(DataConsistencyChecks):

    @classmethod
    def get_reference_curve(cls, record: Record) -> Optional[str]:
        if not record.data:
            return None
        return record.data.get(PPFgDataSetProperties.PRIMARY_REFERENCE_CURVE_ID.value)

    @classmethod
    def check_bulk_consistency(cls, record: Record, bulk_info: BulkInfoForConsistency):
        if not record.data:
            return

        cls._check_columns_consistency(record.data, bulk_info.curves)

    @classmethod
    @_tracer.start_as_current_span("bulk_consistency")
    async def check_bulk_consistency_on_commit_session(cls, record: Record, new_bulk_id):
        pass

    @classmethod
    @_tracer.start_as_current_span("bulk_consistency")
    def check_bulk_consistency_on_post_bulk(cls, record: Record, df: pd.DataFrame):
        if not record.data:
            return

        reference_name = record.data.get(PPFgDataSetProperties.PRIMARY_REFERENCE_CURVE_ID.value)
        if reference_name not in df.columns:
            reference_name = None

        bulk_info = BulkInfoForConsistency(
            rowCount=len(df.index),
            curves=DataConsistencyChecks._get_curve_name_and_column_count(df.columns),
            reference=ColumnDescribe.from_column(df, reference_name) if reference_name else None,
        )
        cls.check_bulk_consistency(record, bulk_info)

    @staticmethod
    def _check_columns_consistency(ppfg_data: dict, curve_sizes: Dict[str, int]):
        """
        Validates the consistency between the column names in bulk data and the curve IDs in the PPFGDataset metadata.

        Args:
            ppfg_data (dict): The metadata of the PPFGDataset containing curve information.
            curve_sizes (Dict[str, int]): A dictionary mapping column names to their respective number of columns.

        Raises:
            ColumnDoesNotMatchCurveIdException: If a column name in `curve_sizes` does not match any CurveID in the metadata
                or if there are no curves in the metadata but `curve_sizes` contains columns.
        """

        curves = ppfg_data.get(PPFgDataSetProperties.CURVES.value)
        if not curves and len(curve_sizes) > 0:
            raise ColumnDoesNotMatchCurveIdException(
                f"Column(s) do(es) not match any {PPFgDataSetProperties.CURVE_ID.value} of the PPFGDataset record."
            )

        curve_sizes_from_meta = {
            c[PPFgDataSetProperties.CURVE_ID.value]: DEFAULT_NUMBER_OF_COLUMNS for c in curves
        }

        not_matching_col_name = curve_sizes.keys() - curve_sizes_from_meta.keys()
        if any(not_matching_col_name):
            raise ColumnDoesNotMatchCurveIdException(
                f"Column(s) {', '.join(not_matching_col_name)} do(es) not match any {PPFgDataSetProperties.CURVE_ID.value}"
                f" of the PPFGDataset record."
            )
