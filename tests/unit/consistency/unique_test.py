from app.consistency.unique import DuplicatedIdError, get_unique_attr_values
from app.model.osdu_model import Curve120


def test_get_unique_ids_success():
    ids, error = get_unique_attr_values(
        [Curve120(CurveID="A"), Curve120(CurveID="B"), Curve120(CurveID="C")], attr_name="CurveID"
    )

    assert ids == {"A", "B", "C"}
    assert error is None

    ids, error = get_unique_attr_values([], attr_name="CurveID")

    assert ids == set()
    assert error is None


def test_get_unique_ids_None():
    ids, error = get_unique_attr_values(
        [Curve120(), Curve120(), Curve120()], attr_name="CurveID"
    )
    assert ids == set()
    assert error is None


def test_get_unique_ids_error():
    ids, error = get_unique_attr_values(
        [Curve120(CurveID="A"), Curve120(CurveID="B"), Curve120(CurveID="A")], attr_name="CurveID"
    )
    assert error is not None
    assert type(error) is DuplicatedIdError
