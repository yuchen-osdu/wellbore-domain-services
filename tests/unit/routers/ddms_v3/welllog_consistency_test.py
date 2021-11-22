import pytest
import json

from fastapi import Header, status
from fastapi.testclient import TestClient

from app.clients import SearchServiceClient, StorageRecordServiceClient

from app.helper import traces
from app.middleware import require_data_partition_id
from app.auth.auth import require_opendes_authorized_user
from app.utils import Context
from app.wdms_app import wdms_app, app_injector

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
        wdms_app.dependency_overrides[
            require_opendes_authorized_user
        ] = bypass_authorization
        wdms_app.dependency_overrides[require_data_partition_id] = set_default_partition
        client = TestClient(wdms_app)
        yield client
    finally:
        wdms_app.dependency_overrides = previous_overrides  # clean up


# Initialize traces exporter in app, like it is in app's startup decorator
wdms_app.trace_exporter = traces.CombinedExporter(service_name="tested-ddms")


@pytest.mark.parametrize("data", [
    {
        "ReferenceCurveID": "MD",
        "Curves": [
            {"CurveID": "GR"},
            {"CurveID": "MD"}
        ]
    },
    {
        "Curves": [
            {"CurveID": "MD"},
            {"CurveID": "GR"}
        ]
    },
    {
        "Curves": [
        ]
    },
    {
        "TopMeasuredDepth":"1000"
    }
])
def test_post_consistent_welllog(client, data):

    response = client.post(
        "/ddms/v3/welllogs",
        data=json.dumps(
            [{
                "kind": "osdu:wks:work-product-component--WellLog:1.0.0",
                "legal": {
                    "legaltags": ["foo"],
                    "otherRelevantDataCountries": ["FR"]
                },
                "acl": {
                    "owners": ["foo@bar.com"],
                    "viewers": ["foo@bar.com"]
                },
                "data": data
            }]
        ),
        headers={'content-type': 'application/json'})

    assert response.status_code == status.HTTP_200_OK


@pytest.mark.parametrize("data, expected", [
    (
        {
            "ReferenceCurveID": "MD",
            "Curves": [
                {"CurveID": "MD"},
                {"CurveID": "ZONE_NAME"},
                {"CurveID": "ZONE_NAME"}
            ]
        },
        (status.HTTP_400_BAD_REQUEST, "Two curves can\'t have same CurveID")
    ),
    (
        {
            "ReferenceCurveID": "MD",
            "Curves": [
                {"CurveID": "A"},
                {"CurveID": "B"}
            ]
        },
        (status.HTTP_400_BAD_REQUEST, "ReferenceCurveID MD not found in wellLog Curves")
    ),
    (
        {
            "ReferenceCurveID": "MD",
            "Curves": []
        },
        (status.HTTP_400_BAD_REQUEST, "ReferenceCurveID MD not found in wellLog Curves")
    ),
    (
        {
            "ReferenceCurveID": "MD"
        },
        (status.HTTP_400_BAD_REQUEST, "ReferenceCurveID MD not found in wellLog Curves")
    )
])
def test_post_inconsistent_welllog(client, data, expected):
    response = client.post(
        "/ddms/v3/welllogs",
        data=json.dumps(
            [{
                "kind": "osdu:wks:work-product-component--WellLog:1.0.0",
                "legal": {
                    "legaltags": ["foo"],
                    "otherRelevantDataCountries": ["FR"]
                },
                "acl": {
                    "owners": ["foo@bar.com"],
                    "viewers": ["foo@bar.com"]
                },
                "data": data
            }]),
        headers={'content-type': 'application/json'})

    assert response.status_code == expected[0]
    assert expected[1] in response.json().get("detail")

