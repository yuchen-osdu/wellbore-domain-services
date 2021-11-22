from app.model.osdu_model import WellLog110 as WellLog


class UniqueCurveIdException(RuntimeError):
    pass


class ReferenceCurveNotFoundException(RuntimeError):
    pass


def welllog_consistency_check(wl: WellLog):
    if not wl.data:
        return

    curve_ids = set()

    # check all curve ids are unique
    # 'any' and generator allows for raising at first error without fetching all curves id
    if wl.data.Curves and any(curve.CurveID in curve_ids or curve_ids.add(curve.CurveID) for curve in wl.data.Curves):
        raise UniqueCurveIdException()

    # check the referenceCurveID in curves
    if wl.data.ReferenceCurveID and wl.data.ReferenceCurveID not in curve_ids:
        raise ReferenceCurveNotFoundException()
