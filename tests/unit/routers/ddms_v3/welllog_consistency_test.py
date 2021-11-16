import copy
import pytest
from app.model.osdu_model import WellLog110, AbstractLegalTags100, AbstractAccessControlList100, WellLogData110, Curve110
from app.routers.ddms_v3.welllog_ddms_v3 import consistency_check
from fastapi import  HTTPException

KIND = "osdu:wks:work-product-component--WellLog:1.0.0"
LEGAL = AbstractLegalTags100(legaltags=["legal_tag"], otherRelevantDataCountries=["FR"], status="compliant")
ACL = AbstractAccessControlList100(owners=["data.default.owners@opendes.slb.com"], viewers=["data.default.viewers@opendes.slb.com"])


@pytest.mark.parametrize("w", [
    WellLog110(
        kind=KIND,
        legal=LEGAL,
        acl=ACL,
        data=WellLogData110(
            ReferenceCurveID="MD",
            Curves=[
                Curve110(CurveID="MD"),
                Curve110(CurveID="ZONE_NAME")
            ]
        )
    ),
    WellLog110(
        kind=KIND,
        legal=LEGAL,
        acl=ACL
    ),
    WellLog110(
        kind=KIND,
        legal=LEGAL,
        acl=ACL,
        data=WellLogData110(
            Curves=[
                Curve110(CurveID="MD"),
                Curve110(CurveID="ZONE_NAME")
            ]
        )
    )
])
def test_consistency_check(w):
    consistency_check(w)


def test_consistency_repeated_curveid():
    with pytest.raises(HTTPException) as excinfo:
        consistency_check(
            WellLog110(
                kind=KIND,
                legal=LEGAL,
                acl=ACL,
                data=WellLogData110(
                    ReferenceCurveID="MD",
                    Curves=[
                        Curve110(CurveID="ZONE_NAME"),
                        Curve110(CurveID="ZONE_NAME")
                    ]
                )
            )
        )
    assert "Two curves can't have same CurveID" in str(excinfo.value.detail)
    assert excinfo.value.status_code == 400


def test_consistency_reference_not_exists():
    with pytest.raises(HTTPException) as excinfo:
        consistency_check(
            WellLog110(
                kind=KIND,
                legal=LEGAL,
                acl=ACL,
                data=WellLogData110(
                    Curves=[
                        Curve110(CurveID="ZONE_NAME"),
                        Curve110(CurveID="ZONE_NAME")
                    ]
                )
            )

        )
    assert "Two curves can't have same CurveID" in str(excinfo.value.detail)
    assert excinfo.value.status_code == 400


def test_consistency_reference_but_not_curve():
    with pytest.raises(HTTPException) as excinfo:
        consistency_check(
            WellLog110(
                kind=KIND,
                legal=LEGAL,
                acl=ACL,
                data=WellLogData110(
                    ReferenceCurveID="FOO"
                )
            )
        )
    assert "ReferenceCurveID FOO not found in wellLog Curves" in str(excinfo.value.detail)
    assert excinfo.value.status_code == 400

