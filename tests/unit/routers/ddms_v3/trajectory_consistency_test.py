from unittest.mock import AsyncMock, create_autospec, patch

from fastapi import status
from odes_storage.models import CreateUpdateRecordsResponse
import pytest

from app.clients import StorageRecordServiceClient


storage_record_service_client_mock = create_autospec(StorageRecordServiceClient, spec_set=True, instance=True)


@pytest.fixture
def client(app_configurable_with_testclient, nope_logger_fixture):
    _, client = app_configurable_with_testclient(
        storage_client_mock=storage_record_service_client_mock,
    )
    return client


legal = {"legaltags": ["foo"], "otherRelevantDataCountries": ["FR"]}
acl = {"owners": ["foo@bar.com"], "viewers": ["foo@bar.com"]}


@pytest.mark.parametrize(
    "available_trajectory_station_properties",
    [
        [
            {
                "Name": "AzimuthTN",
                "TrajectoryStationPropertyTypeID": "partition-id:reference-data--TrajectoryStationPropertyType:AzimuthTN:"
            },
            {
                "Name": "Incl",
                "TrajectoryStationPropertyTypeID": "partition-id:reference-data--TrajectoryStationPropertyType:Inclination:"
            },
        ],
        [
            {
                "TrajectoryStationPropertyTypeID": "partition-id:reference-data--TrajectoryStationPropertyType:AzimuthTN:"
            },
            {
                "TrajectoryStationPropertyTypeID": "partition-id:reference-data--TrajectoryStationPropertyType:Inclination:"
            },
        ],
        [
            {
                "Name": "AzimuthTN",
                "TrajectoryStationPropertyTypeID": "partition-id:reference-data--TrajectoryStationPropertyType:AzimuthTN:"
            },
        ],
        [
            {
                "Name": "MD",
                "TrajectoryStationPropertyTypeID": "partition-id:reference-data--TrajectoryStationPropertyType:MD:"
            },
        ],
        [
            {
                "Name": "Incl",
            },
        ],
        [
            {}
        ],
        [
            {
                "TrajectoryStationPropertyTypeID": "partition-id:reference-data--TrajectoryStationPropertyType:Inclination:"
            }
        ],
        [
            {
                "TrajectoryStationPropertyTypeID": "partition-id:reference-data--TrajectoryStationPropertyType:MD:"
            }
        ],
        [],
        None,
    ],
)
@patch.object(storage_record_service_client_mock, 'create_or_update_records',
              AsyncMock(return_value=CreateUpdateRecordsResponse(recordCount=1, recordIds=['rec1'])))
def test_post_v3_consistent_trajectory(client, available_trajectory_station_properties):
    response = client.post(
        url="/ddms/v3/wellboretrajectories",
        json=[
            {
                "kind": "osdu:wks:work-product-component--WellboreTrajectory:1.1.0",
                "legal": legal,
                "acl": acl,
                "data": {
                    "WellboreID": "namespace:master-data--Wellbore:c7c421a7-f496-5aef-8093-298c32bfdea9:456",
                    "TopDepthMeasuredDepth": 1.0,
                    "BaseDepthMeasuredDepth": 1.0,
                    "VerticalMeasurement": [],
                    "AvailableTrajectoryStationProperties": available_trajectory_station_properties
                },
            }
        ],
        headers={"content-type": "application/json"},
    )
    assert response.status_code == status.HTTP_200_OK


@pytest.mark.parametrize(
    "available_trajectory_station_properties",
    [
        [
            {
                "Name": "Incl",
                "TrajectoryStationPropertyTypeID": "partition-id:reference-data--TrajectoryStationPropertyType:AzimuthTN:"
            },
            {
                "Name": "Incl",
                "TrajectoryStationPropertyTypeID": "partition-id:reference-data--TrajectoryStationPropertyType:Inclination:"
            },
        ],
    ],
)
def test_post_v3_inconsistent_trajectory(client, available_trajectory_station_properties):
    response = client.post(
        url="/ddms/v3/wellboretrajectories",
        json=[
            {
                "kind": "osdu:wks:work-product-component--WellboreTrajectory:1.1.0",
                "legal": legal,
                "acl": acl,
                "data": {
                    "WellboreID": "namespace:master-data--Wellbore:c7c421a7-f496-5aef-8093-298c32bfdea9:456",
                    "TopDepthMeasuredDepth": 1,
                    "BaseDepthMeasuredDepth": 1,
                    "VerticalMeasurement": [],
                    "AvailableTrajectoryStationProperties": available_trajectory_station_properties
                },
            }
        ],
        headers={"content-type": "application/json"},
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "All station properties in WellboreTrajectory[0] should be unique" in response.json().get("detail")

