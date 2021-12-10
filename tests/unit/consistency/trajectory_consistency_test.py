import pytest

from app.consistency import DuplicatedStationProperties, check_trajectory_consistency
from app.model.osdu_model import (
    AbstractAccessControlList100,
    AbstractLegalTags100,
    AvailableTrajectoryStationProperty,
    WellboreTrajectory110,
    WellboreTrajectoryData110,
)

KIND = "osdu:wks:work-product-component--WellboreTrajectory:1.0.0"
LEGAL = AbstractLegalTags100(legaltags=["legal_tag"], otherRelevantDataCountries=["FR"], status="compliant")
ACL = AbstractAccessControlList100(
    owners=["data.default.owners@opendes.slb.com"], viewers=["data.default.viewers@opendes.slb.com"]
)


@pytest.mark.parametrize(
    "available_trajectory_station_properties",
    [
        [
            AvailableTrajectoryStationProperty(
                TrajectoryStationPropertyTypeID="partition-id:reference-data--TrajectoryStationPropertyType:AzimuthTN:"
            ),
            AvailableTrajectoryStationProperty(
                TrajectoryStationPropertyTypeID="partition-id:reference-data--TrajectoryStationPropertyType:INCL:"
            ),
        ],
        [],
        None,
    ],
)
def test_consistency_check_success(available_trajectory_station_properties):
    check_trajectory_consistency(
        WellboreTrajectory110(
            kind=KIND,
            legal=LEGAL,
            acl=ACL,
            data=WellboreTrajectoryData110(
                WellboreID="namespace:master-data--Wellbore:c7c421a7-f496-5aef-8093-298c32bfdea9:456",
                TopDepthMeasuredDepth=10,
                BaseDepthMeasuredDepth=10,
                VerticalMeasurement=[],
                AvailableTrajectoryStationProperties=available_trajectory_station_properties,
            ),
        )
    )


def test_consistency_check_error():
    with pytest.raises(DuplicatedStationProperties) as excinfo:
        check_trajectory_consistency(
            WellboreTrajectory110(
                kind=KIND,
                legal=LEGAL,
                acl=ACL,
                data=WellboreTrajectoryData110(
                    WellboreID="namespace:master-data--Wellbore:c7c421a7-f496-5aef-8093-298c32bfdea9:456",
                    TopDepthMeasuredDepth=10,
                    BaseDepthMeasuredDepth=10,
                    VerticalMeasurement=[],
                    AvailableTrajectoryStationProperties=[
                        AvailableTrajectoryStationProperty(
                            TrajectoryStationPropertyTypeID="partition-id:reference-data--TrajectoryStationPropertyType:AzimuthTN:"
                        ),
                        AvailableTrajectoryStationProperty(
                            TrajectoryStationPropertyTypeID="partition-id:reference-data--TrajectoryStationPropertyType:AzimuthTN:"
                        ),
                    ],
                ),
            )
        )
