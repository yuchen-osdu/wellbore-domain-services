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

    if not wl.data:
        return

    curve_ids = set()

    # check all curve ids are unique
    if wl.data.Curves:
        # expression generator fetch curve_ids and   evaluate on demand if a curve is duplicated
        duplicated = (curve.CurveID in curve_ids or curve_ids.add(curve.CurveID) for curve in wl.data.Curves)
        if any(duplicated):
            raise DuplicatedCurveIdException()

    # Check there is a curve with curveID == referenceCurveID
    if wl.data.ReferenceCurveID and wl.data.ReferenceCurveID not in curve_ids:
        raise ReferenceCurveIdNotFoundException()
