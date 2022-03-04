import pandas as pd
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
