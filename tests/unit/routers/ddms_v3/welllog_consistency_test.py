from unittest.mock import AsyncMock, create_autospec, patch

from fastapi import  status

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


kind = "osdu:wks:work-product-component--WellLog:1.2.0"
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
@patch.object(storage_record_service_client_mock, 'create_or_update_records',
              AsyncMock(return_value=CreateUpdateRecordsResponse(recordCount=1, recordIds=['rec1'])))
@pytest.mark.anyio
async def test_post_v3_consistent_welllog(client, data):
    response = await client.post(
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
@pytest.mark.anyio
async def test_post_inconsistent_welllog(client, well_log_data, expected):
    response = await client.post(
        url="/ddms/v3/welllogs",
        json=[
            {"kind": kind, "legal": legal, "acl": acl, "data": data}
            for data in well_log_data
        ],
        headers={"content-type": "application/json"},
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert expected in response.json().get("detail")

