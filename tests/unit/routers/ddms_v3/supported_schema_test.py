from unittest.mock import AsyncMock, create_autospec, patch

from fastapi import Header, status
from fastapi.testclient import TestClient
from odes_storage.models import CreateUpdateRecordsResponse
import pytest

from app.auth.auth import require_opendes_authorized_user
from app.clients import SearchServiceClient, StorageRecordServiceClient
from app.context import Context
from app.helper import traces
from app.middleware import require_data_partition_id
from app.wdms_app import app_injector, wdms_app

storage_record_service_client_mock = create_autospec(StorageRecordServiceClient, spec_set=True, instance=True)
search_service_client_mock = create_autospec(SearchServiceClient, spec_set=True, instance=True)


@pytest.fixture
def client(nope_logger_fixture):
    async def bypass_authorization():
        # empty method
        pass

    async def set_default_partition(data_partition_id: str = Header("opendes")):
        Context.set_current_with_value(partition_id=data_partition_id)

    async def build_mock_storage():
        return storage_record_service_client_mock

    async def build_mock_search():
        return search_service_client_mock

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


trajectory_data = {
    "WellboreID": "namespace:master-data--Wellbore:c7c421a7-f496-5aef-8093-298c32bfdea9:456",
    "TopDepthMeasuredDepth": 0,
    "BaseDepthMeasuredDepth": 0,
    "VerticalMeasurement": {},
}



@pytest.mark.parametrize(
    "api, record_type, data",
    [
        ("/ddms/v3/wells", "master-data--Well:1.0.0", {}),
        ("/ddms/v3/wells", "master-data--Well:1.1.0", {}),
        ("/ddms/v3/wellbores", "master-data--Wellbore:1.0.0", {}),
        ("/ddms/v3/wellbores", "master-data--Wellbore:1.1.0", {}),
        ("/ddms/v3/wellbores", "master-data--Wellbore:1.1.1", {}),
        ("/ddms/v3/welllogs", "work-product-component--WellLog:1.0.0", {}),
        ("/ddms/v3/welllogs", "work-product-component--WellLog:1.1.0", {}),
        ("/ddms/v3/welllogs", "work-product-component--WellLog:1.0.0", {"TopMeasuredDepth": "10"}),
        ("/ddms/v3/welllogs", "work-product-component--WellLog:1.1.0", {"TopMeasuredDepth": "10", "SamplingStart": "10"}),


        ("/ddms/v3/wellboremarkersets", "work-product-component--WellboreMarkerSet:1.0.0", {}),
        ("/ddms/v3/wellboremarkersets", "work-product-component--WellboreMarkerSet:1.2.0", {}),
        ("/ddms/v3/wellboremarkersets", "work-product-component--WellboreMarkerSet:1.2.1", {}),
        ("/ddms/v3/wellboremarkersets", "work-product-component--WellboreMarkerSet:1.1.0", {   "AvailableMarkerProperties": [
                    {
                        "MarkerPropertyTypeID": "partition-id:reference-data--MarkerPropertyType:MissingThickness:",
                        "MarkerPropertyUnitID": "partition-id:reference-data--UnitOfMeasure:ft:",
                        "Name": "MissingThickness"
                    }]}),
        ("/ddms/v3/wellboretrajectories", "work-product-component--WellboreTrajectory:1.0.0", trajectory_data),
        ("/ddms/v3/wellboretrajectories", "work-product-component--WellboreTrajectory:1.1.0", trajectory_data),
    ],
)
@patch.object(storage_record_service_client_mock, 'create_or_update_records',
              AsyncMock(return_value=CreateUpdateRecordsResponse(recordCount=1, recordIds=['rec1'])))
def test_check_supported_kind(client, api, record_type, data):
    response = client.post(
        url=api,
        json=[
            {
                "kind": f"osdu:wks:{record_type}",
                "legal": {"legaltags": ["foo"], "otherRelevantDataCountries": ["FR"]},
                "acl": {"owners": ["foo@bar.com"], "viewers": ["foo@bar.com"]},
                "data": data,
            }
        ],
        headers={"content-type": "application/json"},
    )
    assert response.status_code == status.HTTP_200_OK


@pytest.mark.parametrize(
    "api, record_type, data",
    [
        ("/ddms/v3/wells", "master-data--foo:1.0.0", {}),
        ("/ddms/v3/wells", "master-data--Well:1.0.1", {}),
        ("/ddms/v3/wells", "master-data--Well:2.0.0", {}),
        ("/ddms/v3/wellbores", "master-data--foo:1.0.0", {}),
        ("/ddms/v3/wellbores", "master-data--Wellbore:1.0.1", {}),
        ("/ddms/v3/wellbores", "master-data--Wellbore:2.0.0", {}),
        ("/ddms/v3/welllogs", "work-product-component--foo:1.0.0", {}),
        ("/ddms/v3/welllogs", "work-product-component--WellLog:1.0.1", {}),
        ("/ddms/v3/welllogs", "work-product-component--WellLog:2.0.0", {}),
        ("/ddms/v3/wellbores", "master-data--foo:1.0.0", {}),
        ("/ddms/v3/wellbores", "master-data--Wellbore:1.0.1", {}),
        ("/ddms/v3/wellbores", "master-data--Wellbore:2.0.0", {}),
        ("/ddms/v3/wellboremarkersets", "work-product-component--foo:1.0.0", {}),
        ("/ddms/v3/wellboremarkersets", "work-product-component--WellboreMarkerSet:1.0.1", {}),
        ("/ddms/v3/wellboremarkersets", "work-product-component--WellboreMarkerSet:2.0.0", {}),
        ("/ddms/v3/wellboretrajectories", "work-product-component--foo:1.0.0", trajectory_data),
        ("/ddms/v3/wellboretrajectories", "work-product-component--WellboreTrajectory:1.0.1", trajectory_data),
        ("/ddms/v3/wellboretrajectories", "work-product-component--WellboreTrajectory:1.2.0", trajectory_data),
        ("/ddms/v3/wellboretrajectories", "work-product-component--WellboreTrajectory:2.0.0", trajectory_data),
    ],
)
def test_check_not_supported_kind(client, api, record_type, data):
    response = client.post(
        url=api,
        json=[
            {
                "kind": f"osdu:wks:{record_type}",
                "legal": {"legaltags": ["foo"], "otherRelevantDataCountries": ["FR"]},
                "acl": {"owners": ["foo@bar.com"], "viewers": ["foo@bar.com"]},
                "data": data,
            }
        ],
        headers={"content-type": "application/json"},
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_invalid_welllog_schema(client):
    # Schema 1.1.0 have a referenceCurveID field but not 1.0.0. So the validation should failed.
    json = [
        {
            "kind": "osdu:wks:work-product-component--WellLog:1.1.0",
            "legal": {"legaltags": ["foo"], "otherRelevantDataCountries": ["FR"]},
            "acl": {"owners": ["foo@bar.com"], "viewers": ["foo@bar.com"]},
            "data": {"LogSource": "foo"},
        },
        {
            "kind": "osdu:wks:work-product-component--WellLog:1.0.0",
            "legal": {"legaltags": ["foo"], "otherRelevantDataCountries": ["FR"]},
            "acl": {"owners": ["foo@bar.com"], "viewers": ["foo@bar.com"]},
            "data": {"TopMeasuredDepth": "10"},
        },
        {
            "kind": "osdu:wks:work-product-component--WellLog:1.0.0",
            "legal": {"legaltags": ["foo"], "otherRelevantDataCountries": ["FR"]},
            "acl": {"owners": ["foo@bar.com"], "viewers": ["foo@bar.com"]},
            "data": {"ReferenceCurveID": "foo"},
        },
    ]

    response = client.post(url="/ddms/v3/welllogs", json=json, headers={"content-type": "application/json"})
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "Record[2] validation against schema 'work-product-component--WellLog:1.0.0' failed" in response.json().get(
        "detail"
    )




def test_invalid_markerset_schema(client):
    json = [
        {
            "kind": "osdu:wks:work-product-component--WellboreMarkerSet:1.0.0",
            "legal": {"legaltags": ["foo"], "otherRelevantDataCountries": ["FR"]},
            "acl": {"owners": ["foo@bar.com"], "viewers": ["foo@bar.com"]},
            "data": {
                "AvailableMarkerProperties": [
                    {
                        "MarkerPropertyTypeID": "partition-id:reference-data--MarkerPropertyType:MissingThickness:",
                        "MarkerPropertyUnitID": "partition-id:reference-data--UnitOfMeasure:ft:",
                        "Name": "MissingThickness"
                    }
                ],
            },
        }
    ]
    response = client.post(url="/ddms/v3/wellboremarkersets", json=json , headers={"content-type": "application/json"})
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "Record[0] validation against schema 'work-product-component--WellboreMarkerSet:1.0.0' failed" in response.json().get(
        "detail"
    )



def test_invalid_trajectory_schema(client):
    json = [
        {
            "kind": "osdu:wks:work-product-component--WellboreTrajectory:1.0.0",
            "legal": {"legaltags": ["foo"], "otherRelevantDataCountries": ["FR"]},
            "acl": {"owners": ["foo@bar.com"], "viewers": ["foo@bar.com"]},
            "data": {
                "WellboreID":"namespace:master-data--Wellbore:c7c421a7-f496-5aef-8093-298c32bfdea9:456",
                "TopDepthMeasuredDepth": 10,
                "BaseDepthMeasuredDepth": 10,
                "VerticalMeasurement": [],
                "AppliedOperations":["op1", "op2"]
            }
        },

    ]
    response = client.post(url="/ddms/v3/wellboretrajectories", json=json , headers={"content-type": "application/json"})
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "Record[0] validation against schema 'work-product-component--WellboreTrajectory:1.0.0" in response.json().get(
        "detail"
    )
