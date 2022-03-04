import pandas as pd
import pytest


from app.consistency.reference_check import check_reference_is_strictly_monotonic, ReferenceCurveException




def test_check_reference_is_strictly_monotonic_success():
    check_reference_is_strictly_monotonic(pd.Series([0, 1, 2, 3, 4]))
    check_reference_is_strictly_monotonic(pd.Series())


@pytest.mark.parametrize(
    "ref, error",
    [
        ([0, 1, 1, 2, 3, 4], "Repeated values in a reference curve aren't allowed."),
        ([0, None, 1, 2, 3, 4], "Nan values in a reference curve are not allowed."),
        ([0, 2, 4, 3, 5], "Reference must be monotonically increasing or decreasing."),
    ],
)
def test_check_reference_is_strictly_monotonic_error(ref, error):
    with pytest.raises(ReferenceCurveException, match=f"^{error}$") as excinfo:
        check_reference_is_strictly_monotonic(pd.Series(ref))

