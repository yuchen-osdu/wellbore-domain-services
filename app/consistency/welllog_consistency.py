from .unique import get_unique_ids
from app.model.osdu_model import WellLog110


class DuplicatedCurveIdException(RuntimeError):
    """raised if all curveID values are not unique"""


class ReferenceCurveIdNotFoundException(RuntimeError):
    """raised when there is no curve with a curveID value equal to the ReferenceCurveID value"""


def welllog_consistency_check(wl: WellLog110):
    """Check if wellLog is consistent.

    Each curves in data.Curves must have a unique CurveID.
    Welllog must have a curve whose curveID value is equal to the  wellLog's ReferenceCurveID value

    Args:
        wl (Welllog): wellLog object to be verified

    Returns:

    Raises:
        DuplicatedCurveIdException: All CurveIDs are not unique.
        ReferenceCurveIdNotFoundException: No curve whose curveID value are equal to ReferenceCurveID value.
    """
    if wl.data.ReferenceCurveID and (not wl.data or not wl.data.Curves):
        raise ReferenceCurveIdNotFoundException()

    curve_ids, duplicated_error = get_unique_ids(wl.data.Curves, "CurveID")

    if duplicated_error:
        raise DuplicatedCurveIdException()

    # Check there is a curve with curveID == referenceCurveID
    if wl.data.ReferenceCurveID and wl.data.ReferenceCurveID not in curve_ids:
        raise ReferenceCurveIdNotFoundException()
