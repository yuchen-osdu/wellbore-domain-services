import pytest
from app.consistency import TrajectoryDataConsistencyChecks


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


@pytest.fixture
def trajectory():
    return WellboreTrajectory110(kind=KIND, legal=LEGAL, acl=ACL)


mini_traj_data = {
    "WellboreID": "data_partition:master-data--Wellbore:72e872c3f86848cd860689ae48d3b6b1:",
    "TopDepthMeasuredDepth": 0.0,
    "BaseDepthMeasuredDepth": 1.0,
    "VerticalMeasurement": [],
}


@pytest.mark.parametrize(
    "trajectory_data, expected",
    [
        (WellboreTrajectoryData110(**mini_traj_data), None),
        (WellboreTrajectoryData110(**mini_traj_data, AvailableTrajectoryStationProperties=None), None),
        (WellboreTrajectoryData110(**mini_traj_data, AvailableTrajectoryStationProperties=[]), None),
        (
            WellboreTrajectoryData110(
                **mini_traj_data, AvailableTrajectoryStationProperties=[AvailableTrajectoryStationProperty()]
            ),
            None,
        ),
        (
            WellboreTrajectoryData110(
                **mini_traj_data,
                AvailableTrajectoryStationProperties=[
                    AvailableTrajectoryStationProperty(
                        Name="Incl",
                        TrajectoryStationPropertyTypeID=(
                            "data_partition:reference-data--TrajectoryStationPropertyType:Inclination:"
                        ),
                    )
                ],
            ),
            None,
        ),
        (
            WellboreTrajectoryData110(
                **mini_traj_data,
                AvailableTrajectoryStationProperties=[
                    AvailableTrajectoryStationProperty(
                        Name="",
                        TrajectoryStationPropertyTypeID=(
                            "data_partition:reference-data--TrajectoryStationPropertyType:Inclination:"
                        ),
                    )
                ],
            ),
            None,
        ),
        (
            WellboreTrajectoryData110(
                **mini_traj_data,
                AvailableTrajectoryStationProperties=[
                    AvailableTrajectoryStationProperty(
                        Name=None,
                        TrajectoryStationPropertyTypeID=(
                            "data_partition:reference-data--TrajectoryStationPropertyType:Inclination:"
                        ),
                    )
                ],
            ),
            None,
        ),
        (
            WellboreTrajectoryData110(
                **mini_traj_data,
                AvailableTrajectoryStationProperties=[
                    AvailableTrajectoryStationProperty(
                        Name="MD",
                        TrajectoryStationPropertyTypeID=(
                            "data_partition:reference-data--TrajectoryStationPropertyType:MD:"
                        ),
                    )
                ],
            ),
            "MD",
        ),
        (
            WellboreTrajectoryData110(
                **mini_traj_data,
                AvailableTrajectoryStationProperties=[
                    AvailableTrajectoryStationProperty(
                        Name="",
                        TrajectoryStationPropertyTypeID=(
                            "data_partition:reference-data--TrajectoryStationPropertyType:MD:"
                        ),
                    )
                ],
            ),
            None,
        ),
        (
            WellboreTrajectoryData110(
                **mini_traj_data,
                AvailableTrajectoryStationProperties=[
                    AvailableTrajectoryStationProperty(
                        Name=None,
                        TrajectoryStationPropertyTypeID=(
                            "data_partition:reference-data--TrajectoryStationPropertyType:MD:"
                        ),
                    )
                ],
            ),
            None,
        ),
        (
            WellboreTrajectoryData110(
                **mini_traj_data,
                AvailableTrajectoryStationProperties=[
                    AvailableTrajectoryStationProperty(
                        Name="Incl",
                        TrajectoryStationPropertyTypeID=(
                            "data_partition:reference-data--TrajectoryStationPropertyType:Inclination:"
                        ),
                    ),
                    AvailableTrajectoryStationProperty(
                        Name="MD",
                        TrajectoryStationPropertyTypeID=(
                            "data_partition:reference-data--TrajectoryStationPropertyType:MD:"
                        ),
                    ),
                ],
            ),
            "MD",
        ),
    ],
)
def test_get_reference_name(trajectory_data, expected):
    computed = TrajectoryDataConsistencyChecks._get_reference_name(trajectory_data.dict())
    assert computed == expected
