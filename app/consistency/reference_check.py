import pandas as pd
import math
from pydantic import BaseModel
from app.bulk_persistence.consistency_checks import ConsistencyException, DataConsistencyChecks


class ReferenceCurveException(ConsistencyException):
    """raised when column doesn't match any CurveID"""


def check_reference_is_strictly_monotonic(ref: pd.Series):
    # check unique values because is_monotonic_increasing & is_monotonic_decreasing are not strict
    if ref.duplicated().any():
        raise ReferenceCurveException("Repeated values in a reference curve aren't allowed.")

    if not ref.is_monotonic_increasing and not ref.is_monotonic_decreasing:
        # Nan values
        if ref.isnull().values.any():
            raise ReferenceCurveException("Nan values in a reference curve are not allowed.")
        else:
            raise ReferenceCurveException("Reference must be monotonically increasing or decreasing.")


def raise_if_attr_value_is_different(
    record_data: BaseModel,
    attr_name: str,
    reference_value: float,
    error_msg: str,
):
    attr_value = getattr(record_data, attr_name, None)
    if attr_value is not None and not math.isclose(attr_value, reference_value):
        raise ReferenceCurveException(
            error_msg.format(
                attr_name=attr_name,
                attr_value=attr_value,
                reference_value=reference_value,
            )
        )


