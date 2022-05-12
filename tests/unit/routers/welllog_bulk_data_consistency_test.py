import pytest
from app.clients import SearchServiceClient, StorageRecordServiceClient
from tests.unit.test_utils import create_mock_class
import re

StorageRecordServiceClientMock = create_mock_class(StorageRecordServiceClient)
SearchServiceClientMock = create_mock_class(SearchServiceClient)


@pytest.fixture
def dasked_test_app_client(testing_app_local_chunking_with_consistency):
    _, client = testing_app_local_chunking_with_consistency

    return client


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


def _post_data(client, record_id, data):
    return client.post(
        url=f"/ddms/v3/welllogs/{record_id}/data",
        json=data,
        headers={"content-type": "application/json"},
    )


def _create_session(client, record_id):
    response = client.post(f"/ddms/v3/welllogs/{record_id}/sessions", json={"mode": "overwrite"})
    assert response.status_code == 200
    session_id = response.json()["id"]
    return session_id


def _post_chunk(client, record_id, session_id, data):
    response = client.post(f"/ddms/v3/welllogs/{record_id}/sessions/{session_id}/data", json=data)

    return response


def _commit_session(client, record_id, session_id):
    response = client.patch(f"/ddms/v3/welllogs/{record_id}/sessions/{session_id}", json={"state": "commit"})
    return response


def generate_test_data():

    bulk_values = [
        [0.0, 2222.1],
        [0.5, 2222.2],
        [2.0, 2222.5]
    ]
    bulk_data = {
        "columns": ["MD", "GR"],
        "data": bulk_values
    }

    curves_data = {
        "Curves": [
            {"CurveID": "MD"},
            {"CurveID": "GR"},
        ],
    }

    def value_with_tolerance(v):
        rel_tol = 9e-10
        delta = abs(v) * rel_tol
        return v+delta

    reference_curve_data = [
        {"ReferenceCurveID": "MD"},
        {"ReferenceCurveID": ""},
        {"ReferenceCurveID": None},
        {}
    ]
    top_measured_depth_data = [
        {"TopMeasuredDepth": value_with_tolerance(bulk_values[0][0])},
        {"TopMeasuredDepth": None},
        {}
    ]
    sampling_start_data = [
        {"SamplingStart": value_with_tolerance(bulk_values[0][0])},
        {"SamplingStart": None},
        {}
    ]
    bottom_measured_depth_data = [
        {"BottomMeasuredDepth": value_with_tolerance(bulk_values[-1][0])},
        {"BottomMeasuredDepth": None},
        {}
    ]
    sampling_stop_data = [
        {"SamplingStop": value_with_tolerance(bulk_values[-1][0])},
        {"SamplingStop": None},
        {}
    ]

    test_data = []
    for reference_curve in reference_curve_data:
        for top_measured_depth in top_measured_depth_data:
            for sampling_start in sampling_start_data:
                for bottom_measured_depth in bottom_measured_depth_data:
                    for sampling_stop in sampling_stop_data:
                        test_data.append(
                            pytest.param(
                                {
                                    **curves_data,
                                    **reference_curve,
                                    **top_measured_depth,
                                    **sampling_start,
                                    **bottom_measured_depth,
                                    **sampling_stop
                                },
                                bulk_data
                            )
                        )

    return test_data


test_param = generate_test_data()


test_param.append(
    pytest.param(
        {
            "TopMeasuredDepth": 99,
            "BottomMeasuredDepth": 99,
            "SamplingStart": 99,
            "SamplingStop": 99,
            "Curves": [
                {"CurveID": "MD"},
                {"CurveID": "GR"},
            ],
        },
        {
            "columns": ["GR"],
            "data":  [[0.0]],
        }
    )
)

test_param.append(
    pytest.param(
        {
            "TopMeasuredDepth": 99,
            "BottomMeasuredDepth": 99,
            "SamplingStart": 99,
            "SamplingStop": 99,
            "ReferenceCurveID": "MD",
            "Curves": [
                {"CurveID": "MD"},
                {"CurveID": "GR"}
            ],
        },
        {
            "columns": ["GR"],
            "data":  [[0.0]],
        }
    )
)


@pytest.mark.parametrize("welllog_data, bulk_data", test_param)
def test_post_consistent_bulk(dasked_test_app_client, welllog_data, bulk_data):
    wid = _create_record(client=dasked_test_app_client, data=welllog_data)
    response = _post_data(client=dasked_test_app_client, record_id=wid, data=bulk_data)
    assert response.status_code == 200


@pytest.mark.parametrize("welllog_data, bulk_data", test_param)
def test_post_consistent_chunk(dasked_test_app_client, welllog_data, bulk_data):
    wid = _create_record(dasked_test_app_client, welllog_data)
    session_id = _create_session(dasked_test_app_client, wid)

    response = _post_chunk(dasked_test_app_client, wid, session_id, bulk_data)
    assert response.status_code == 200

    response = _commit_session(dasked_test_app_client, wid, session_id)
    assert response.status_code == 200


inconsistent_test_params = [
    pytest.param(
        {"ReferenceCurveID": "MD", "Curves": [{"CurveID": "MD"}, {"CurveID": "GR"}]},
        {"columns": ["MD", "AA"], "data": [[0.0, 2222.1], [0.5, 2222.2], [1.0, 2222.3], [1.5, 2222.4], [2.0, 2222.5]]},
        r"^Column\(s\) AA do\(es\) not match any CurveID of the WellLog record\.$",
    ),
    pytest.param(
        {"ReferenceCurveID": "MD", "Curves": [{"CurveID": "MD"}, {"CurveID": "GR"}]},
        {"columns": ["BB", "AA"], "data": [[0.0, 2222.1], [0.5, 2222.2], [1.0, 2222.3], [1.5, 2222.4], [2.0, 2222.5]]},
        r"^Column\(s\) ((\bAA, BB\b)|(\bBB, AA\b)) do\(es\) not match any CurveID of the WellLog record\.$",
    ),
    pytest.param(
        {
            "ReferenceCurveID": "MD",
            "Curves": [{"CurveID": "MD"}, {"CurveID": "GR"}],
            "SamplingStart": 0.1,
            "SamplingStop": 2.0,
        },
        {"columns": ["MD", "GR"], "data": [[0.0, 2222.1], [0.5, 2222.2], [1.0, 2222.3], [1.5, 2222.4], [2.0, 2222.5]]},
        r"^Reference top value \(0\.0\) is different from SamplingStart value \(0\.1\) of the WellLog record\.$",
    ),
    pytest.param(
        {
            "ReferenceCurveID": "MD",
            "Curves": [{"CurveID": "MD"}, {"CurveID": "GR"}],
            "SamplingStart": 0.0,
            "SamplingStop": 1.9,
        },
        {"columns": ["MD", "GR"], "data": [[0.0, 2222.1], [0.5, 2222.2], [1.0, 2222.3], [1.5, 2222.4], [2.0, 2222.5]]},
        r"^Reference bottom value \(2\.0\) is different from SamplingStop value \(1\.9\) of the WellLog record\.$",
    ),
    pytest.param(
        {"ReferenceCurveID": "MD", "Curves": [{"CurveID": "MD"}, {"CurveID": "GR"}]},
        {"columns": ["MD", "GR"], "data": [[0.0, 2222.1], [0.5, 2222.2], [1.0, 2222.3], [0.9, 2222.4], [2.0, 2222.5]]},
        r"^Reference must be monotonically increasing or decreasing\.$",
    ),
    pytest.param(
        {"ReferenceCurveID": "MD", "Curves": [{"CurveID": "MD"}, {"CurveID": "GR"}]},
        {"columns": ["MD", "GR"], "data": [[0.0, 2222.1], [0.5, 2222.2], [1.0, 2222.3], [1.5, 2222.4], [None, 2222.5]]},
        r"^Nan values in a reference curve are not allowed\.$",
    ),
    pytest.param(
        {"ReferenceCurveID": "MD", "Curves": [{"CurveID": "MD"}, {"CurveID": "GR"}]},
        {"columns": ["MD", "GR"], "data": [[0.0, 2222.1], [0.5, 2222.2], [1.0, 2222.3], [1.0, 2222.4], [2.0, 2222.5]]},
        r"^Repeated values in a reference curve aren't allowed\.$",
    ),
]


@pytest.mark.parametrize("welllog_data, bulk_data, err", inconsistent_test_params)
def test_post_inconsistent_whole_bulk(dasked_test_app_client, welllog_data, bulk_data, err):
    wid = _create_record(dasked_test_app_client, welllog_data)
    response = _post_data(dasked_test_app_client, wid, bulk_data)

    assert response.status_code == 400
    computed = response.json()["detail"]
    pattern = re.compile(err)
    match = pattern.match(computed)

    assert match, f"{computed} should match regular expression {err}"


@pytest.mark.parametrize("welllog_data, bulk_data, err", inconsistent_test_params)
def test_post_inconsistent_chunk(dasked_test_app_client, welllog_data, bulk_data, err):
    wid = _create_record(dasked_test_app_client, welllog_data)
    session_id = _create_session(dasked_test_app_client, wid)

    response = _post_chunk(dasked_test_app_client, wid, session_id, bulk_data)
    assert response.status_code == 200

    response = _commit_session(dasked_test_app_client, wid, session_id)
    assert response.status_code == 400
    computed = response.json()["detail"]
    pattern = re.compile(err)
    match = pattern.match(computed)

    assert match, f"{computed} should match regular expression {err}"
