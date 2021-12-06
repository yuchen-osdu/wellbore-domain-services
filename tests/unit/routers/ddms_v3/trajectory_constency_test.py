import pytest
from fastapi import Header, status
from fastapi.testclient import TestClient

from app.auth.auth import require_opendes_authorized_user
from app.clients import SearchServiceClient, StorageRecordServiceClient
from app.helper import traces
from app.middleware import require_data_partition_id
from app.utils import Context
from app.wdms_app import app_injector, wdms_app
from tests.unit.test_utils import create_mock_class, nope_logger_fixture

StorageRecordServiceClientMock = create_mock_class(StorageRecordServiceClient)
SearchServiceClientMock = create_mock_class(SearchServiceClient)


@pytest.fixture
def client(nope_logger_fixture):
    async def bypass_authorization():
        # empty method
        pass

    async def set_default_partition(data_partition_id: str = Header("opendes")):
        Context.set_current_with_value(partition_id=data_partition_id)

    async def build_mock_storage():
        return StorageRecordServiceClientMock()

    async def build_mock_search():
        return SearchServiceClientMock()

    app_injector.register(StorageRecordServiceClient, build_mock_storage)
    app_injector.register(SearchServiceClient, build_mock_search)

    # override authentication dependency
    previous_overrides = wdms_app.dependency_overrides

    try:
        wdms_app.dependency_overrides[require_opendes_authorized_user] = bypass_authorization
        wdms_app.dependency_overrides[require_data_partition_id] = set_default_partition
        client = TestClient(wdms_app)
        yield client
    finally:
        wdms_app.dependency_overrides = previous_overrides  # clean up


# Initialize traces exporter in app, like it is in app's startup decorator
wdms_app.trace_exporter = traces.CombinedExporter(service_name="tested-ddms")

legal = {"legaltags": ["foo"], "otherRelevantDataCountries": ["FR"]}
acl = {"owners": ["foo@bar.com"], "viewers": ["foo@bar.com"]}


@pytest.mark.parametrize(
    "available_trajectory_station_properties",
    [
        [
            {
                "TrajectoryStationPropertyTypeID": "partition-id:reference-data--TrajectoryStationPropertyType:AzimuthTN:"
            },
            {"TrajectoryStationPropertyTypeID": "partition-id:reference-data--TrajectoryStationPropertyType:INCL:"},
        ],
        [
            {
                "TrajectoryStationPropertyTypeID": "partition-id:reference-data--TrajectoryStationPropertyType:AzimuthTN:"
            },
        ],
        [],
        None,
    ],
)
def test_post_v3_consistent_trajectory(client, available_trajectory_station_properties):
    response = client.post(
        url="/ddms/v3/wellboretrajectories",
        json=[
            {
                "kind": "osdu:wks:work-product-component--WellLog:1.0.0",
                "legal": legal,
                "acl": acl,
                "data": {
                    "WellboreID": "namespace:master-data--Wellbore:c7c421a7-f496-5aef-8093-298c32bfdea9:456",
                    "TopDepthMeasuredDepth": 1,
                    "BaseDepthMeasuredDepth": 1,
                    "VerticalMeasurement": [],
                    "AvailableTrajectoryStationProperties": available_trajectory_station_properties
                    if available_trajectory_station_properties
                    else None,
                },
            }
        ],
        headers={"content-type": "application/json"},
    )
    assert response.status_code == status.HTTP_200_OK


def test_post_v3_inconsistent_trajectory(client):

    trajs = [
        [
            "partition-id:reference-data--TrajectoryStationPropertyType:A:",
            "partition-id:reference-data--TrajectoryStationPropertyType:B:",
        ],
        [
            "partition-id:reference-data--TrajectoryStationPropertyType:A:",
            "partition-id:reference-data--TrajectoryStationPropertyType:A:",
        ],
        [
            "partition-id:reference-data--TrajectoryStationPropertyType:A:",
            "partition-id:reference-data--TrajectoryStationPropertyType:B:",
        ],
    ]

    j = [
        {
            "kind": "osdu:wks:work-product-component--WellLog:1.0.0",
            "legal": legal,
            "acl": acl,
            "data": {
                "WellboreID": "namespace:master-data--Wellbore:c7c421a7-f496-5aef-8093-298c32bfdea9:456",
                "TopDepthMeasuredDepth": 1,
                "BaseDepthMeasuredDepth": 1,
                "VerticalMeasurement": [],
                "AvailableTrajectoryStationProperties": [{"TrajectoryStationPropertyTypeID": i} for i in t],
            },
        }
        for t in trajs
    ]

    response = client.post(
        url="/ddms/v3/wellboretrajectories",
        json=j,
        headers={"content-type": "application/json"},
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "All station properties in WellboreTrajectory[1] should be unique" in response.json().get("detail")
