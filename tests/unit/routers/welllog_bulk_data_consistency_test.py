import pytest
from app.clients import SearchServiceClient, StorageRecordServiceClient
from fastapi.testclient import TestClient
from tests.unit.test_utils import create_mock_class
from tests.unit.test_utils import nope_logger_fixture
from .chunking_test import dasked_test_app


StorageRecordServiceClientMock = create_mock_class(StorageRecordServiceClient)
SearchServiceClientMock = create_mock_class(SearchServiceClient)


@pytest.fixture
def dasked_test_app_client(dasked_test_app):
    yield TestClient(dasked_test_app)


def _create_record(client, data):
    record = {
        "kind": "osdu:wks:work-product-component--WellLog:1.1.0",
        "acl": {"owners": ["foo@bar.com"], "viewers": ["foo@bar.com"]},
        "legal": {
            "legaltags": ["opendes-storage-1602183747123"],
            "otherRelevantDataCountries": ["US"],
        },
        "version": 0,
        "data": data,
    }
    response = client.post("/ddms/v3/welllogs", json=[record])
    assert response.status_code == 200
    record_id = response.json()["recordIds"][0]
    return record_id


def _post_data(client, wid, data):
    return client.post(
        url=f"/ddms/v3/welllogs/{wid}/data",
        json=data,
        headers={"content-type": "application/json"},
    )


def _create_session(client, wid):
    response = client.post(f"/ddms/v3/welllogs/{wid}/sessions", json={"mode": "overwrite"})
    assert response.status_code == 200
    session_id = response.json()["id"]
    return session_id


def _post_chunk(client, wid, session_id, data):
    response = client.post(f"/ddms/v3/welllogs/{wid}/sessions/{session_id}/data", json=data)

    return response


def _commit_session(client, wid, session_id):
    response = client.patch(f"/ddms/v3/welllogs/{wid}/sessions/{session_id}", json={"state": "commit"})
    return response


def test_consistent_whole_bulk(dasked_test_app_client):
    wid = _create_record(
        dasked_test_app_client,
        {
            "ReferenceCurveID": "MD",
            "Curves": [
                {"CurveID": "MD"},
                {"CurveID": "GR"},
            ],
            "TopMeasuredDepth": "0.0",
            "SamplingStart": "0.0",
            "BottomMeasuredDepth": "2.0",
            "SamplingStop": "2.0",
        },
    )

    response = _post_data(
        dasked_test_app_client,
        wid,
        {"columns": ["MD", "GR"], "data": [[0.0, 2222.1], [0.5, 2222.2], [1.0, 2222.3], [1.5, 2222.4], [2.0, 2222.5]]},
    )

    assert response.status_code == 200


inconsistent_test_params = [
    pytest.param(
        {"ReferenceCurveID": "MD", "Curves": [{"CurveID": "MD"}, {"CurveID": "GR"}]},
        {"columns": ["MD", "AA"], "data": [[0.0, 2222.1], [0.5, 2222.2], [1.0, 2222.3], [1.5, 2222.4], [2.0, 2222.5]]},
        "Column(s) AA doesn't match any CurveID",
    ),
    pytest.param(
        {
            "ReferenceCurveID": "MD",
            "Curves": [{"CurveID": "MD"}, {"CurveID": "GR"}],
            "TopMeasuredDepth": 0.1,
            "BottomMeasuredDepth": 2.0,
        },
        {"columns": ["MD", "GR"], "data": [[0.0, 2222.1], [0.5, 2222.2], [1.0, 2222.3], [1.5, 2222.4], [2.0, 2222.5]]},
        "Reference TopMeasuredDepth value (0.0) is not egal to welllog's TopMeasuredDepth value (0.1)",
    ),
    pytest.param(
        {
            "ReferenceCurveID": "MD",
            "Curves": [{"CurveID": "MD"}, {"CurveID": "GR"}],
            "TopMeasuredDepth": 0.0,
            "BottomMeasuredDepth": 1.9,
        },
        {"columns": ["MD", "GR"], "data": [[0.0, 2222.1], [0.5, 2222.2], [1.0, 2222.3], [1.5, 2222.4], [2.0, 2222.5]]},
        "Reference BottomMeasuredDepth value (2.0) is not egal to welllog's BottomMeasuredDepth value (1.9)",
    ),
    pytest.param(
        {"ReferenceCurveID": "MD", "Curves": [{"CurveID": "MD"}, {"CurveID": "GR"}]},
        {"columns": ["MD", "GR"], "data": [[0.0, 2222.1], [0.5, 2222.2], [1.0, 2222.3], [0.9, 2222.4], [2.0, 2222.5]]},
        "Reference must be monotonically increasing or decreasing",
    ),
    pytest.param(
        {"ReferenceCurveID": "MD", "Curves": [{"CurveID": "MD"}, {"CurveID": "GR"}]},
        {"columns": ["MD", "GR"], "data": [[0.0, 2222.1], [0.5, 2222.2], [1.0, 2222.3], [1.5, 2222.4], [None, 2222.5]]},
        "Nan values in reference curve is not allowed",
    ),
    pytest.param(
        {"ReferenceCurveID": "MD", "Curves": [{"CurveID": "MD"}, {"CurveID": "GR"}]},
        {"columns": ["MD", "GR"], "data": [[0.0, 2222.1], [0.5, 2222.2], [1.0, 2222.3], [1.0, 2222.4], [2.0, 2222.5]]},
        "Reference curve must have only unique values",
    ),
]


@pytest.mark.parametrize("welllog_data, bulk_data, err", inconsistent_test_params)
def test_post_inconsistent_whole_bulk(dasked_test_app_client, welllog_data, bulk_data, err):
    wid = _create_record(dasked_test_app_client, welllog_data)
    response = _post_data(dasked_test_app_client, wid, bulk_data)

    assert response.status_code == 400
    assert err in response.text


@pytest.mark.parametrize("welllog_data, bulk_data, err", inconsistent_test_params)
def test_post_inconsistent_chunk(dasked_test_app_client, welllog_data, bulk_data, err):
    wid = _create_record(dasked_test_app_client, welllog_data)
    session_id = _create_session(dasked_test_app_client, wid)

    response = _post_chunk(dasked_test_app_client, wid, session_id, bulk_data)
    assert response.status_code == 200

    response = _commit_session(dasked_test_app_client, wid, session_id)
    assert response.status_code == 400
    assert err in response.text
