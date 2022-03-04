import pytest
from app.clients import SearchServiceClient, StorageRecordServiceClient
from fastapi.testclient import TestClient
from tests.unit.test_utils import create_mock_class
from .chunking_test import dasked_test_app


StorageRecordServiceClientMock = create_mock_class(StorageRecordServiceClient)
SearchServiceClientMock = create_mock_class(SearchServiceClient)


@pytest.fixture
def dasked_test_app_client(dasked_test_app, nope_logger_fixture):
    yield TestClient(dasked_test_app)


def _create_record(client, data):
    record = {
        "kind": "osdu:wks:work-product-component--WellboreTrajectory:1.1.0",
        "acl": {"owners": ["foo@bar.com"], "viewers": ["foo@bar.com"]},
        "legal": {
            "legaltags": ["opendes-storage-1602183747123"],
            "otherRelevantDataCountries": ["US"],
        },
        "version": 0,
        "data": data,
    }
    response = client.post("/ddms/v3/wellboretrajectories", json=[record])
    assert response.status_code == 200
    record_id = response.json()["recordIds"][0]
    return record_id


def _post_data(client, wid, data):
    return client.post(
        url=f"/ddms/v3/wellboretrajectories/{wid}/data",
        json=data,
        headers={"content-type": "application/json"},
    )


def _create_session(client, wid):
    response = client.post(f"/ddms/v3/wellboretrajectories/{wid}/sessions", json={"mode": "overwrite"})
    assert response.status_code == 200
    session_id = response.json()["id"]
    return session_id


def _post_chunk(client, wid, session_id, data):
    response = client.post(f"/ddms/v3/wellboretrajectories/{wid}/sessions/{session_id}/data", json=data)

    return response


def _commit_session(client, wid, session_id):
    response = client.patch(f"/ddms/v3/wellboretrajectories/{wid}/sessions/{session_id}", json={"state": "commit"})
    return response


@pytest.mark.parametrize(
    "traj_data, bulk_data",
    [
        (
            {
                "WellboreID": "partition-id:master-data--Wellbore:72e872c3f86848cd860689ae48d3b6b1:",
                "TopDepthMeasuredDepth": "0",
                "BaseDepthMeasuredDepth": "0",
                "VerticalMeasurement": [],
                "AvailableTrajectoryStationProperties": [
                    {
                        "Name": "MD",
                        "TrajectoryStationPropertyTypeID": "partition-id:reference-data--TrajectoryStationPropertyType:MD:",
                    },
                    {
                        "Name": "Incl",
                        "TrajectoryStationPropertyTypeID": "partition-id:reference-data--TrajectoryStationPropertyType:Inclination:"
                    },
                ],
            },
            {
                "columns": ["MD", "Incl"],
                "data": [
                    [0.0, 2222.1],
                    [2.0, 2222.5]
                ]
            }
        ),
    ]
)
def test_consistent_whole_bulk(dasked_test_app_client, traj_data, bulk_data):
    record_id = _create_record(
        dasked_test_app_client,
        data=traj_data
    )

    response = _post_data(dasked_test_app_client, record_id, bulk_data)

    assert response.status_code == 200


@pytest.mark.parametrize(
    "traj_data, bulk_data, err",
    [
         (
            {
                "WellboreID": "partition-id:master-data--Wellbore:72e872c3f86848cd860689ae48d3b6b1:",
                "TopDepthMeasuredDepth": "0",
                "BaseDepthMeasuredDepth": "0",
                "VerticalMeasurement": [],
                "AvailableTrajectoryStationProperties": []
            },
            {
                "columns": ["MD", "Incl"],
                "data": [
                    [0.0, 2222.1],
                    [2.0, 2222.5]
                ]
            },
            "Column(s) MD,Incl do(es) not match any AvailableTrajectoryStationProperties name in the WellboreTrajectory record.",
        ),
    ]
)
def test_inconsistent_whole_bulk(dasked_test_app_client, traj_data, bulk_data, err):
    record_id = _create_record(
        dasked_test_app_client,
        data=traj_data
    )

    response = _post_data(dasked_test_app_client, record_id, bulk_data)

    assert response.status_code == 400

    assert err in response.text






