from app.consistency.unique import DuplicatedIdError, get_unique_ids
from app.model.osdu_model import Curve110


def test_get_unique_ids_success():
    ids, error = get_unique_ids(
        [Curve110(CurveID="A"), Curve110(CurveID="B"), Curve110(CurveID="C")], attr_name="CurveID"
    )

    assert ids == {"A", "B", "C"}
    assert error is None

    ids, error = get_unique_ids([], attr_name="CurveID")

    assert ids == set()
    assert error is None


def test_get_unique_ids_error():
    ids, error = get_unique_ids(
        [Curve110(CurveID="A"), Curve110(CurveID="B"), Curve110(CurveID="A")], attr_name="CurveID"
    )
    assert error is not None
    assert type(error) is DuplicatedIdError
