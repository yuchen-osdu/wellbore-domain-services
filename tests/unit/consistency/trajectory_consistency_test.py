import pytest
from pydantic import BaseModel

from app.consistency import TrajectoryDataConsistencyChecks
from odes_storage.models import Record
from tests.unit.test_utils import make_record

KIND = "osdu:wks:work-product-component--WellboreTrajectory:1.0.0"
LEGAL = {"legaltags": ["legal_tag"], "otherRelevantDataCountries":["FR"], "status":"compliant"}
ACL = {"owners": ["data.default.owners@opendes.slb.com"], "viewers": ["data.default.viewers@opendes.slb.com"]}


@pytest.fixture
def trajectory():
    return Record(kind=KIND, legal=LEGAL, acl=ACL)


mini_traj_data = {
    "WellboreID": "data_partition:master-data--Wellbore:72e872c3f86848cd860689ae48d3b6b1:",
    "TopDepthMeasuredDepth": 0.0,
    "BaseDepthMeasuredDepth": 1.0,
    "VerticalMeasurement": {},
}

class AvailableTrajectoryStationProperty(BaseModel):
    Name: str | None = None
    TrajectoryStationPropertyTypeID: str | None = None

class WellboreTrajectoryData(BaseModel):
    WellboreID: str
    TopDepthMeasuredDepth: float
    BaseDepthMeasuredDepth: float
    VerticalMeasurement: dict
    AvailableTrajectoryStationProperties: list[AvailableTrajectoryStationProperty] | None = None

@pytest.mark.parametrize(
    "trajectory_data, expected",
    [
        (WellboreTrajectoryData(**mini_traj_data), None),
        (WellboreTrajectoryData(**mini_traj_data, AvailableTrajectoryStationProperties=None), None),
        (WellboreTrajectoryData(**mini_traj_data, AvailableTrajectoryStationProperties=[]), None),
        (
            WellboreTrajectoryData(
                **mini_traj_data, AvailableTrajectoryStationProperties=[AvailableTrajectoryStationProperty()]
            ),
            None,
        ),
        (
            WellboreTrajectoryData(
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
            WellboreTrajectoryData(
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
            WellboreTrajectoryData(
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
            WellboreTrajectoryData(
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
            WellboreTrajectoryData(
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
            WellboreTrajectoryData(
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
            WellboreTrajectoryData(
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
    record = make_record(data=trajectory_data.model_dump())
    computed = TrajectoryDataConsistencyChecks.get_reference_curve(record)
    assert computed == expected
