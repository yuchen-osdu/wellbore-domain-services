import pytest

from app.consistency import DuplicatedCurveIdException, ReferenceCurveIdNotFoundException, welllog_consistency_check
from app.model.osdu_model import (
    AbstractAccessControlList100,
    AbstractLegalTags100,
    Curve110,
    WellLog110,
    WellLogData110,
)

KIND = "osdu:wks:work-product-component--WellLog:1.1.0"
LEGAL = AbstractLegalTags100(legaltags=["legal_tag"], otherRelevantDataCountries=["FR"], status="compliant")
ACL = AbstractAccessControlList100(
    owners=["data.default.owners@opendes.slb.com"], viewers=["data.default.viewers@opendes.slb.com"]
)


@pytest.mark.parametrize(
    "data",
    [
        WellLogData110(ReferenceCurveID="MD", Curves=[Curve110(CurveID="MD"), Curve110(CurveID="ZONE_NAME")]),
        WellLogData110(Curves=[Curve110(CurveID="MD"), Curve110(CurveID="ZONE_NAME")]),
        WellLogData110(Curves=[]),
    ],
)
def test_consistency_check(data):
    welllog_consistency_check(WellLog110(kind=KIND, legal=LEGAL, acl=ACL, data=data))


@pytest.mark.parametrize(
    "data",
    [
        WellLogData110(
            ReferenceCurveID="MD",
            Curves=[Curve110(CurveID="ZONE_NAME"), Curve110(CurveID="ZONE_NAME"), Curve110(CurveID="MD")],
        ),
        WellLogData110(Curves=[Curve110(CurveID="ZONE_NAME"), Curve110(CurveID="ZONE_NAME")]),
    ],
)
def test_consistency_inconsistent_curves_welllog(data):
    with pytest.raises(DuplicatedCurveIdException) as excinfo:
        welllog_consistency_check(WellLog110(kind=KIND, legal=LEGAL, acl=ACL, data=data))


@pytest.mark.parametrize(
    "data",
    [
        WellLogData110(ReferenceCurveID="MD", Curves=[Curve110(CurveID="ZONE_NAME"), Curve110(CurveID="A")]),
        WellLogData110(ReferenceCurveID="MD", Curves=[Curve110(CurveID="A"), Curve110(CurveID="B")]),
        WellLogData110(ReferenceCurveID="MD"),
    ],
)
def test_consistency_inconsistent_reference_id_welllog(data):
    with pytest.raises(ReferenceCurveIdNotFoundException) as excinfo:
        welllog_consistency_check(WellLog110(kind=KIND, legal=LEGAL, acl=ACL, data=data))
