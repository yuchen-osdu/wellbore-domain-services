from unittest import mock
import pytest
import pandas as pd
from deepdiff import DeepDiff

from app.consistency.welllog_consistency import (
    WelllogDataConsistencyChecks,
    check_welllog_consistency,
    ColumnDoesNotMatchCurveIdException,
    DuplicatedCurveIdException,
    ReferenceCurveIdNotFoundException,
    ReferenceCurveException
)

from app.model.osdu_model import (
    AbstractAccessControlList100,
    AbstractLegalTags100,
    Curve110,
    WellLog110,
    WellLogData110,
)

ID = "osdu:work-product-component--WellLog:dcac5c42114d4dd28d186860da9bc9be"
KIND = "osdu:wks:work-product-component--WellLog:1.1.0"
LEGAL = AbstractLegalTags100(legaltags=["legal_tag"], otherRelevantDataCountries=["FR"], status="compliant")
ACL = AbstractAccessControlList100(
    owners=["data.default.owners@opendes.slb.com"], viewers=["data.default.viewers@opendes.slb.com"]
)


@pytest.fixture
def welllog():
    return WellLog110(kind=KIND, legal=LEGAL, acl=ACL)


@pytest.mark.parametrize(
    "data",
    [
        WellLogData110(ReferenceCurveID="MD", Curves=[Curve110(CurveID="MD"), Curve110(CurveID="ZONE_NAME")]),
        WellLogData110(Curves=[Curve110(CurveID="MD"), Curve110(CurveID="ZONE_NAME")]),
        WellLogData110(Curves=[]),
    ],
)
def test_consistency_check(welllog, data):
    welllog.data = data
    check_welllog_consistency(WellLog110(kind=KIND, legal=LEGAL, acl=ACL, data=data))


@pytest.mark.parametrize("data", [
    WellLogData110(
        ReferenceCurveID="MD",
        Curves=[
            Curve110(CurveID="ZONE_NAME"),
            Curve110(CurveID="ZONE_NAME"),
            Curve110(CurveID="MD")
        ]
    ),
    WellLogData110(
        Curves=[
            Curve110(CurveID="ZONE_NAME"),
            Curve110(CurveID="ZONE_NAME")
        ]
    )
])
def test_consistency_inconsistent_curves_welllog(welllog, data):
    with pytest.raises(DuplicatedCurveIdException) as excinfo:
        welllog.data = data
        check_welllog_consistency(WellLog110(kind=KIND, legal=LEGAL, acl=ACL, data=data))


@pytest.mark.parametrize("data", [
    WellLogData110(ReferenceCurveID="MD", Curves=[Curve110(CurveID="A"), Curve110(CurveID="B")]),
    WellLogData110(ReferenceCurveID="MD")])
def test_consistency_inconsistent_reference_id_welllog(welllog, data):
    with pytest.raises(ReferenceCurveIdNotFoundException) as excinfo:
        welllog.data = data
        check_welllog_consistency(welllog)


@pytest.mark.asyncio
async def test_check_columns_consistency_error(welllog):
    welllog.data = WellLogData110(Curves=[Curve110(CurveID="A"), Curve110(CurveID="D")])

    with pytest.raises(
        ColumnDoesNotMatchCurveIdException, match=r"^Column\(s\)  [B,C]|[C,B] doesn't match any CurveID$"
    ) as excinfo:
        await WelllogDataConsistencyChecks._check_columns_consistency(welllog, ["A","B","C","D"])


def test_get_data_columns_name():
    computed = WelllogDataConsistencyChecks._get_data_columns_name(["GR[1]", "GR[2]", "DEN[1324]", "VSHALE[1324]", "", "A[1324][456]"])

    assert not DeepDiff(computed, {"GR", "DEN", "VSHALE", "A[1324]"})

    assert WelllogDataConsistencyChecks._get_data_columns_name([]) == set()
    assert WelllogDataConsistencyChecks._get_data_columns_name([""]) == set()
    assert WelllogDataConsistencyChecks._get_data_columns_name(["[foo]"]) == {"[foo]"}
    assert WelllogDataConsistencyChecks._get_data_columns_name(["[1234]"]) == {"[1234]"}


def test__check_reference_is_strictly_monotonic_success():
    WelllogDataConsistencyChecks._check_reference_is_strictly_monotonic(pd.Series([0, 1, 2, 3, 4]))
    WelllogDataConsistencyChecks._check_reference_is_strictly_monotonic(pd.Series())


@pytest.mark.parametrize(
    "ref, error",
    [
        (
            [0, 1, 1, 2, 3, 4],
            "Reference curve must have only unique values"
        ),
        (
                [0, None, 1, 2, 3, 4],
                "Nan values in reference curve are not allowed"
         ),
        (
                [0, 2, 4, 3, 5],
                "Reference must be monotonically increasing or decreasing"
        ),
    ]
)
def test__check_reference_is_strictly_monotonic_error(ref, error):
    with pytest.raises(
            ReferenceCurveException, match=f"^{error}$"
    ) as excinfo:
        WelllogDataConsistencyChecks._check_reference_is_strictly_monotonic(pd.Series(ref))


@pytest.mark.parametrize(
    "welllog_data, data, columns",
    [
        (
                WellLogData110(),
                [],
                []
        ),
        (
            WellLogData110(
                Curves=[Curve110(CurveID="MD"), Curve110(CurveID="GR")]),
            [[0.0, 12], [1.0, 45], ],
            ["MD", "GR"]
        ),
        (
            WellLogData110(
                TopMeasuredDepth=0.0,
                BottomMeasuredDepth=1.0,
                Curves=[Curve110(CurveID="MD"), Curve110(CurveID="GR")]),
            [[0.0, 12], [1.0, 45], ],
            ["MD", "GR"]
        ),
        (
            WellLogData110(
                TopMeasuredDepth=0.0,
                BottomMeasuredDepth=1.000001,
                Curves=[Curve110(CurveID="MD"), Curve110(CurveID="GR")]),
            [[0.0, 12], [1.0, 45], ],
            ["MD", "GR"]
        ),
        (
                WellLogData110(
                    SamplingStart=0.0,
                    SamplingStop=1.0,
                    Curves=[Curve110(CurveID="MD"), Curve110(CurveID="GR")]),
                [[0.0, 12], [1.0, 45], ],
                ["MD", "GR"]
        ),
        (
            WellLogData110(
                ReferenceCurveID="MD",
                TopMeasuredDepth=0.0,
                BottomMeasuredDepth=1.0,
                SamplingStart=0.0,
                SamplingStop=1.0,
                Curves=[Curve110(CurveID="MD"), Curve110(CurveID="GR")]),
            [[0.0, 12], [1.0, 45], ],
            ["MD", "GR"]
        ),
    ]
)
def test_check_bulk_consistency_on_post_bulk(welllog, welllog_data, data, columns):
    df = pd.DataFrame(data=data, columns=columns)
    welllog.data = welllog_data
    WelllogDataConsistencyChecks.check_bulk_consistency_on_post_bulk(welllog, df)
