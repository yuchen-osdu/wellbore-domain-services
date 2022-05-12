import pytest
from fastapi import Header, status
from fastapi.testclient import TestClient

from app.auth.auth import require_opendes_authorized_user
from app.clients import SearchServiceClient, StorageRecordServiceClient
from app.helper import traces
from app.middleware import require_data_partition_id
from app.context import Context
from app.wdms_app import app_injector, wdms_app
from tests.unit.test_utils import create_mock_class

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
        # Initialize traces exporter in app, like it is in app's startup decorator
        wdms_app.trace_exporter = traces.CombinedExporter(service_name="tested-ddms")
        client = TestClient(wdms_app)

        yield client
    finally:
        wdms_app.dependency_overrides = previous_overrides  # clean up


kind = "osdu:wks:work-product-component--WellLog:1.1.0"
legal = {"legaltags": ["foo"], "otherRelevantDataCountries": ["FR"]}
acl = {"owners": ["foo@bar.com"], "viewers": ["foo@bar.com"]}


@pytest.mark.parametrize(
    "data",
    [
        [
            {"ReferenceCurveID": "MD", "Curves": [{"CurveID": "GR"}, {"CurveID": "MD"}]},
            {"ReferenceCurveID": "TVD", "Curves": [{"CurveID": "TVD"}, {"CurveID": "INCL"}]},
            {"ReferenceCurveID": None, "Curves": None},
            {"ReferenceCurveID": None, "Curves": []},
            {"Curves": [{"CurveID": "MD"}, {"CurveID": "GR"}]},
            {"Curves": [{"CurveID": "GR"}, {"CurveID": None}]},
            {"Curves": [{"CurveID": None}]},
            {"Curves": []},
            {"Curves": None},
            {}
        ],
    ],
)
def test_post_v3_consistent_welllog(client, data):
    response = client.post(
        url="/ddms/v3/welllogs",
        json=[
            {"kind": kind, "legal": legal, "acl": acl, "data": d}
            for d in data
        ],
        headers={"content-type": "application/json"},
    )

    assert response.status_code == status.HTTP_200_OK


@pytest.mark.parametrize(
    "well_log_data, expected",
    [
        (
                [
                    {"Curves": [{"CurveID": "MD"}, {"CurveID": "GR"}]},
                    {"Curves": [{"CurveID": "MD"}, {"CurveID": "A"}, {"CurveID": "A"}]},
                    {"Curves": [{"CurveID": "MD"}, {"CurveID": "B"}]},
                ],
                "All CurveID in WellLog[1] should be unique",
        ),
        (
                [
                    {"Curves": [{"CurveID": None}, {"CurveID": None}]},
                    {"Curves": [{"CurveID": "MD"}, {"CurveID": "A"}, {"CurveID": "A"}]},
                    {"Curves": [{"CurveID": "MD"}, {"CurveID": "B"}]},
                ],
                "All CurveID in WellLog[1] should be unique",
        ),
        (
                [
                    {"ReferenceCurveID": "MD", "Curves": [{"CurveID": "MD"}, {"CurveID": "GR"}]},
                    {"ReferenceCurveID": "MD", "Curves": [{"CurveID": "MD"}, {"CurveID": "A"}, {"CurveID": "A"}]},
                    {"ReferenceCurveID": "MD", "Curves": [{"CurveID": "MD"}, {"CurveID": "B"}]},
                ],
                "All CurveID in WellLog[1] should be unique",
        ),
        (
                [
                    {"ReferenceCurveID": "MD", "Curves": [{"CurveID": "MD"}, {"CurveID": "GR"}]},
                    {"ReferenceCurveID": "MD", "Curves": [{"CurveID": "A"}, {"CurveID": "B"}]},
                    {"ReferenceCurveID": "MD", "Curves": [{"CurveID": "MD"}, {"CurveID": "C"}]},
                ],
                "WellLog[1] should have a curve with a curveID value equal to the ReferenceCurveID value: 'MD'",
        ),
        (
                [
                    {"ReferenceCurveID": "MD", "Curves": [{"CurveID": "MD"}, {"CurveID": "GR"}]},
                    {"ReferenceCurveID": "MD", "Curves": []},
                    {"ReferenceCurveID": "MD", "Curves": [{"CurveID": "MD"}, {"CurveID": "B"}]},
                ],
                "WellLog[1] should have a curve with a curveID value equal to the ReferenceCurveID value: 'MD'",
        ),
        (
                [
                    {"ReferenceCurveID": "MD", "Curves": [{"CurveID": "MD"}, {"CurveID": "GR"}]},
                    {"ReferenceCurveID": "MD", "Curves": None},
                    {"ReferenceCurveID": "MD", "Curves": [{"CurveID": "MD"}, {"CurveID": "B"}]},
                ],
                "WellLog[1] should have a curve with a curveID value equal to the ReferenceCurveID value: 'MD'",
        ),
        (
                [
                    {"ReferenceCurveID": "MD", "Curves": [{"CurveID": "MD"}, {"CurveID": "GR"}]},
                    {"ReferenceCurveID": "MD"},
                    {"ReferenceCurveID": "MD", "Curves": [{"CurveID": "MD"}, {"CurveID": "B"}]},
                    {"ReferenceCurveID": "MD", "Curves": [{"CurveID": "MD"}, {"CurveID": "B"}]},
                ],
                "WellLog[1] should have a curve with a curveID value equal to the ReferenceCurveID value: 'MD'",
        ),
    ],
)
def test_post_inconsistent_welllog(client, well_log_data, expected):
    response = client.post(
        url="/ddms/v3/welllogs",
        json=[
            {"kind": kind, "legal": legal, "acl": acl, "data": data}
            for data in well_log_data
        ],
        headers={"content-type": "application/json"},
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert expected in response.json().get("detail")

