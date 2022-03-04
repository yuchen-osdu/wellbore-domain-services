import pytest
import pandas as pd
from app.consistency import DuplicatedStationProperties, check_trajectory_consistency, TrajectoryDataConsistencyChecks


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


@pytest.mark.parametrize(
    "available_trajectory_station_properties",
    [
        [
            AvailableTrajectoryStationProperty(
                Name="AzimuthTN",
                TrajectoryStationPropertyTypeID="partition-id:reference-data--TrajectoryStationPropertyType:AzimuthTN:"
            ),
            AvailableTrajectoryStationProperty(
                Name="Incl",
                TrajectoryStationPropertyTypeID="partition-id:reference-data--TrajectoryStationPropertyType:Inclination:"
            ),
        ],
        [
            AvailableTrajectoryStationProperty()
        ],
        [
            AvailableTrajectoryStationProperty(Name="Incl")
        ],
        [
            AvailableTrajectoryStationProperty(TrajectoryStationPropertyTypeID="partition-id:reference-data--TrajectoryStationPropertyType:Inclination:")
        ],
        [],
        None,
    ],
)
def test_consistency_check_trajectory_consistency_success(available_trajectory_station_properties):
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


def test_consistency_check_trajectory_consistency_error():
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
                            Name="AzimuthTN",
                            TrajectoryStationPropertyTypeID="partition-id:reference-data--TrajectoryStationPropertyType:AzimuthTN:"
                        ),
                        AvailableTrajectoryStationProperty(
                            Name="AzimuthTN",
                            TrajectoryStationPropertyTypeID="partition-id:reference-data--TrajectoryStationPropertyType:Inclination:"
                        ),
                    ],
                ),
            )
        )

@pytest.mark.parametrize(
    "trajectory_data, expected",
    [
        (
                WellboreTrajectoryData110(
                    WellboreID="data_partition:master-data--Wellbore:72e872c3f86848cd860689ae48d3b6b1:",
                    TopDepthMeasuredDepth=0,
                    BaseDepthMeasuredDepth=0,
                    VerticalMeasurement=[],
                ),
                None
        ),
        (
                WellboreTrajectoryData110(
                    WellboreID="data_partition:master-data--Wellbore:72e872c3f86848cd860689ae48d3b6b1:",
                    TopDepthMeasuredDepth=0,
                    BaseDepthMeasuredDepth=0,
                    VerticalMeasurement=[],
                    AvailableTrajectoryStationProperties=[
                        AvailableTrajectoryStationProperty(
                            TrajectoryStationPropertyTypeID="data_partition:reference-data--TrajectoryStationPropertyType:MD:",
                        ),
                        AvailableTrajectoryStationProperty(
                            Name="Incl",
                            TrajectoryStationPropertyTypeID="data_partition:reference-data--TrajectoryStationPropertyType:Inclination:",
                        ),
                    ]
                ),
                None
        ),
        (
                WellboreTrajectoryData110(
                    WellboreID="data_partition:master-data--Wellbore:72e872c3f86848cd860689ae48d3b6b1:",
                    TopDepthMeasuredDepth=0,
                    BaseDepthMeasuredDepth=0,
                    VerticalMeasurement=[],
                    AvailableTrajectoryStationProperties=[
                        AvailableTrajectoryStationProperty(
                            Name="MD",
                            TrajectoryStationPropertyTypeID="data_partition:reference-data--TrajectoryStationPropertyType:MD:",
                        ),
                        AvailableTrajectoryStationProperty(
                            Name="Incl",
                            TrajectoryStationPropertyTypeID="data_partition:reference-data--TrajectoryStationPropertyType:Inclination:",
                        ),
                    ]
                ),
                "MD"
        ),

        (
                WellboreTrajectoryData110(
                    WellboreID="data_partition:master-data--Wellbore:72e872c3f86848cd860689ae48d3b6b1:",
                    TopDepthMeasuredDepth=0,
                    BaseDepthMeasuredDepth=0,
                    VerticalMeasurement=[],
                    AvailableTrajectoryStationProperties=[
                        AvailableTrajectoryStationProperty(
                            Name="Incl",
                            TrajectoryStationPropertyTypeID="data_partition:reference-data--TrajectoryStationPropertyType:Inclination:",
                        ),
                        AvailableTrajectoryStationProperty(
                            Name="MD",
                            TrajectoryStationPropertyTypeID="data_partition:reference-data--TrajectoryStationPropertyType:MD:",
                        ),
                    ]
                ),
                "MD"
        ),
    ],
)
def test_get_reference_name(trajectory, trajectory_data, expected):
    trajectory.data = trajectory_data
    computed = TrajectoryDataConsistencyChecks.get_reference_name(trajectory)
    assert computed == expected


@pytest.mark.parametrize(
    "trajectory_data, data, columns",
    [
        (
                WellboreTrajectoryData110(
                    WellboreID="data_partition:master-data--Wellbore:72e872c3f86848cd860689ae48d3b6b1:",
                    TopDepthMeasuredDepth=0,
                    BaseDepthMeasuredDepth=0,
                    VerticalMeasurement=[],
                ),
                [],
                []
        ),
        (
                WellboreTrajectoryData110(
                    WellboreID="data_partition:master-data--Wellbore:72e872c3f86848cd860689ae48d3b6b1:",
                    TopDepthMeasuredDepth=0,
                    BaseDepthMeasuredDepth=0,
                    VerticalMeasurement=[],
                    AvailableTrajectoryStationProperties=[
                        AvailableTrajectoryStationProperty(
                            Name="Az",
                            TrajectoryStationPropertyTypeID="data_partition:reference-data--TrajectoryStationPropertyType:Azimuth:",
                        ),
                        AvailableTrajectoryStationProperty(
                            Name="Incl",
                            TrajectoryStationPropertyTypeID="data_partition:reference-data--TrajectoryStationPropertyType:Inclination:",
                        ),
                    ]
                ),
                [
                    [0.0, 12],
                    [1.0, 45],
                ],
                ["Az", "Incl"]
        ),
        (
                WellboreTrajectoryData110(
                    WellboreID="data_partition:master-data--Wellbore:72e872c3f86848cd860689ae48d3b6b1:",
                    TopDepthMeasuredDepth=0,
                    BaseDepthMeasuredDepth=0,
                    VerticalMeasurement=[],
                    AvailableTrajectoryStationProperties=[
                        AvailableTrajectoryStationProperty(
                            Name="MD",
                            TrajectoryStationPropertyTypeID="data_partition:reference-data--TrajectoryStationPropertyType:MD:",
                        ),
                        AvailableTrajectoryStationProperty(
                            Name="Incl",
                            TrajectoryStationPropertyTypeID="data_partition:reference-data--TrajectoryStationPropertyType:Inclination:",
                        ),
                    ]
                ),
                [
                    [0.0, 12],
                    [1.0, 45],
                ],
                ["MD", "Incl"]
        ),
    ],
)
def test_check_bulk_consistency_on_post_bulk(trajectory, trajectory_data, data, columns):
    df = pd.DataFrame(data=data, columns=columns)
    trajectory.data = trajectory_data
    TrajectoryDataConsistencyChecks.check_bulk_consistency_on_post_bulk(trajectory, df)
