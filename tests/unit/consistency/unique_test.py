from pydantic import BaseModel

from app.consistency.unique import DuplicatedIdError, get_unique_attr_values

class Curve(BaseModel):
    CurveID: str | None = None

def test_get_unique_ids_success():
    ids, error = get_unique_attr_values(
        [Curve(CurveID="A"), Curve(CurveID="B"), Curve(CurveID="C")], attr_name="CurveID"
    )

    assert ids == {"A", "B", "C"}
    assert error is None

    ids, error = get_unique_attr_values([], attr_name="CurveID")

    assert ids == set()
    assert error is None


def test_get_unique_ids_None():
    ids, error = get_unique_attr_values(
        [Curve(), Curve(), Curve()], attr_name="CurveID"
    )
    assert ids == set()
    assert error is None


def test_get_unique_ids_error():
    ids, error = get_unique_attr_values(
        [Curve(CurveID="A"), Curve(CurveID="B"), Curve(CurveID="A")], attr_name="CurveID"
    )
    assert error is not None
    assert type(error) is DuplicatedIdError
