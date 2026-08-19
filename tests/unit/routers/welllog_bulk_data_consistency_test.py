import copy
import pytest


@pytest.fixture
def test_app_client(testing_app_local_chunking_with_consistency):
    _, client = testing_app_local_chunking_with_consistency

    return client


record = {
    "kind": "osdu:wks:work-product-component--WellLog:1.1.0",
    "acl": {"owners": ["foo@bar.com"], "viewers": ["foo@bar.com"]},
    "legal": {
        "legaltags": ["opendes-storage-1602183747123"],
        "otherRelevantDataCountries": ["US"],
    },
    "version": 0
}


async def _create_record(client, data, header):
    record["data"] = data
    response = await client.post("/ddms/v3/welllogs", json=[record], headers=header)
    assert response.status_code == 200
    record_id = response.json()["recordIds"][0]
    return record_id


async def _post_data(client, record_id, data, header):
    resp = await client.post(
        url=f"/ddms/v3/welllogs/{record_id}/data",
        json=data,
        headers={
            **header,
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    print(resp)
    return resp


async def _create_session(client, record_id, header):
    response = await client.post(f"/ddms/v3/welllogs/{record_id}/sessions",
                                 json={"mode": "overwrite"},
                                 headers=header)
    assert response.status_code == 200
    session_id = response.json()["id"]
    return session_id


async def _post_chunk(client, record_id, session_id, data, header):
    response = await client.post(f"/ddms/v3/welllogs/{record_id}/sessions/{session_id}/data",
                                 json=data,
                                 headers=header)

    return response


async def _commit_session(client, record_id, session_id, header):
    response = await client.patch(f"/ddms/v3/welllogs/{record_id}/sessions/{session_id}",
                                  json={"state": "commit"},
                                  headers=header)
    return response


def generate_test_data():

    bulk_values = [
        [0.0, 0.5, 2222.2, 0.5],
        [0.5, 0.5, 2222.2, 0.5],
        [2.0, 0.5, 2222.2, 0.5]
    ]
    bulk_data = {
        "columns": ["MD", "GR[0]", "GR[1]", "GR[2]"],
        "data": bulk_values
    }
    def value_with_tolerance(v):
        rel_tol = 9e-10
        delta = abs(v) * rel_tol
        return v + delta


    nominal_case = {
        "Curves": [
            {"CurveID": "MD", "NumberOfColumns": 1, "LogCurveFamilyID": "osdu:reference-data--LogCurveFamily:Measured%20Depth:"},
            {"CurveID": "GR", "NumberOfColumns": 3},
        ],
        "ReferenceCurveID": "MD",
        "TopMeasuredDepth": value_with_tolerance(bulk_values[0][0]),
        "SamplingStart": value_with_tolerance(bulk_values[0][0]),
        "BottomMeasuredDepth": value_with_tolerance(bulk_values[-1][0]),
        "BottomMeasuredDepth": value_with_tolerance(bulk_values[-1][0]),
    }

    other_cases = [
        {
        "Curves": [
            {"CurveID": "MD", "NumberOfColumns": 1},
            {"CurveID": "GR", "NumberOfColumns": 3},
        ]},
        {"Curves": [
            {"CurveID": "MD", "NumberOfColumns": 1
                , "LogCurveFamilyID": None
             },
            {"CurveID": "GR", "NumberOfColumns": 3},
        ]},
        {"ReferenceCurveID": None},
        {"TopMeasuredDepth": None},
        {"SamplingStart": None},
        {"BottomMeasuredDepth": None},
        {"SamplingStop": None},
    ]

    test_data = [
        pytest.param(
            {
                **nominal_case
            },
            bulk_data
        )
    ]

    for other in other_cases:
        dict_3 = dict(nominal_case , **other)
        test_data.append(
            pytest.param(
                {
                    **dict_3
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
                {"CurveID": "MD", "NumberOfColumns": 1},
                {"CurveID": "GR", "NumberOfColumns": 1},
            ],
        },
        {
            "columns": ["MD", "GR"],
            "data": [[0.0, 0.0]],
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
                {"CurveID": "MD", "NumberOfColumns": 1},
                {"CurveID": "GR", "NumberOfColumns": 1}
            ],
        },
        {
            "columns": ["MD", "GR"],
            "data": [[0.0, 0.0]],
        }
    )
)


@pytest.mark.parametrize("welllog_data, bulk_data", test_param)
@pytest.mark.anyio
async def test_post_consistent_bulk(test_app_client, welllog_data, bulk_data, local_partition_header):
    wid = await _create_record(client=test_app_client, data=welllog_data, header=local_partition_header)
    response = await _post_data(client=test_app_client, record_id=wid, data=bulk_data, header=local_partition_header)
    assert response.status_code == 200


@pytest.mark.parametrize("welllog_data, bulk_data", test_param)
@pytest.mark.anyio
async def test_post_consistent_chunk(test_app_client, welllog_data, bulk_data, local_partition_header):
    wid = await _create_record(test_app_client, welllog_data, local_partition_header)
    session_id = await _create_session(test_app_client, wid, local_partition_header)

    response = await _post_chunk(test_app_client, wid, session_id, bulk_data, local_partition_header)
    assert response.status_code == 200

    response = await _commit_session(test_app_client, wid, session_id, local_partition_header)
    assert response.status_code == 200


inconsistent_test_params_column_unmatch_curve_id_and_number_of_columns = [
    pytest.param(
        {"ReferenceCurveID": "MD", "Curves": [{"CurveID": "MD", "NumberOfColumns": 1}, {"CurveID": "GR", "NumberOfColumns": 1}]},
        {"columns": ["MD", "AA"], "data": [[0.0, 2222.1], [0.5, 2222.2], [1.0, 2222.3], [1.5, 2222.4], [2.0, 2222.5]]},
        "Column(s) AA do(es) not match any CurveID of the WellLog record"
    ),
    pytest.param(
        {"ReferenceCurveID": "MD", "Curves": [{"CurveID": "MD", "NumberOfColumns": 1}, {"CurveID": "GR", "NumberOfColumns": 1}]},
        {"columns": ["AA", "BB"], "data": [[0.0, 2222.1], [0.5, 2222.2], [1.0, 2222.3], [1.5, 2222.4], [2.0, 2222.5]]},
        "do(es) not match any CurveID of the WellLog record"
    ),
    pytest.param(
        {"ReferenceCurveID": "MD",
         "Curves": [{"CurveID": "MD", "NumberOfColumns": 2}, {"CurveID": "GR", "NumberOfColumns": 1}]},
        {"columns": ["MD", "GR"], "data": [[0.0, 2222.1], [0.5, 2222.2], [1.0, 2222.3], [1.5, 2222.4], [2.0, 2222.5]]},
         "The number of columns for curve(s): {'MD': 1} in the bulk data do(es) not match the 'NumberOfColumns' property value in the WellLog record for CurveID: {'MD': 2}"
    )
]

inconsistent_test_params = [
    pytest.param(
        {
            "ReferenceCurveID": "MD",
            "Curves": [{"CurveID": "MD", "NumberOfColumns": 1}, {"CurveID": "GR", "NumberOfColumns": 1}],
            "SamplingStart": 0.1,
            "SamplingStop": 2.0,
        },
        {"columns": ["MD", "GR"], "data": [[0.0, 2222.1], [0.5, 2222.2], [1.0, 2222.3], [1.5, 2222.4], [2.0, 2222.5]]},
        "Reference top value (0.0) is different from SamplingStart value (0.1) of the WellLog record",
    ),
    pytest.param(
        {
            "ReferenceCurveID": "MD",
            "Curves": [{"CurveID": "MD", "NumberOfColumns": 1}, {"CurveID": "GR", "NumberOfColumns": 1}],
            "SamplingStart": 0.0,
            "SamplingStop": 1.9,
        },
        {"columns": ["MD", "GR"], "data": [[0.0, 2222.1], [0.5, 2222.2], [1.0, 2222.3], [1.5, 2222.4], [2.0, 2222.5]]},
        "Reference bottom value (2.0) is different from SamplingStop value (1.9) of the WellLog record"
    ),
    pytest.param(
        {"ReferenceCurveID": "MD", "Curves": [{"CurveID": "MD", "NumberOfColumns": 1}, {"CurveID": "GR", "NumberOfColumns": 1}]},
        {"columns": ["MD", "GR"], "data": [[0.0, 2222.1], [0.5, 2222.2], [1.0, 2222.3], [0.9, 2222.4], [2.0, 2222.5]]},
        "The reference curve \'MD\' should be monotonic"
    ),
    pytest.param(
        {"ReferenceCurveID": "MD", "Curves": [{"CurveID": "MD", "NumberOfColumns": 1}, {"CurveID": "GR", "NumberOfColumns": 1}]},
        {"columns": ["MD", "GR"], "data": [[0.0, 2222.1], [0.5, 2222.2], [1.0, 2222.3], [1.5, 2222.4], [None, 2222.5]]},
        "The reference curve \'MD\' should not contains missing values",
    ),
    pytest.param(
        {"ReferenceCurveID": "MD", "Curves": [{"CurveID": "MD", "NumberOfColumns": 1}, {"CurveID": "GR", "NumberOfColumns": 1}]},
        {"columns": ["MD", "GR"], "data": [[0.0, 2222.1], [0.5, 2222.2], [1.0, 2222.3], [1.0, 2222.4], [2.0, 2222.5]]},
        "The reference curve \'MD\' should not contains duplicated values",
    ),
]


@pytest.mark.parametrize("wrong_log_curve_family", [{"LogCurveFamilyID": ""}, {"LogCurveFamilyID": "TEST"}])
@pytest.mark.parametrize("welllog_data, bulk_data, err", inconsistent_test_params_column_unmatch_curve_id_and_number_of_columns)
@pytest.mark.anyio
async def test_post_inconsistent_whole_bulk_column_unmatch_curve_id_wrong_log_curve_family(test_app_client, welllog_data,
                                                                                           bulk_data, err, wrong_log_curve_family,
                                                                                           local_partition_header):
    # because accessing to welllog_data modifies the value for next tests
    my_welllog_data = copy.deepcopy(welllog_data)
    my_welllog_data["Curves"][0].update(wrong_log_curve_family)
    record["data"] = my_welllog_data
    response = await test_app_client.post("/ddms/v3/welllogs", json=[record], headers=local_partition_header)

    assert response.status_code == 422


@pytest.mark.parametrize("no_log_curve_family", [{"LogCurveFamilyID": None}, {}])
@pytest.mark.parametrize("welllog_data, bulk_data, err", inconsistent_test_params_column_unmatch_curve_id_and_number_of_columns  )
@pytest.mark.anyio
async def test_post_inconsistent_whole_bulk_column_unmatch_curve_id_no_log_curve_family(test_app_client, welllog_data,
                                                                                        bulk_data, err, no_log_curve_family,
                                                                                        local_partition_header):
    # because accessing to welllog_data modifies the value for next tests
    my_welllog_data = copy.deepcopy(welllog_data)
    my_welllog_data["Curves"][0].update(no_log_curve_family)
    record["data"] = my_welllog_data
    response = await test_app_client.post("/ddms/v3/welllogs", json=[record], headers=local_partition_header)

    assert response.status_code == 200
    wid = response.json()["recordIds"][0]

    response = await _post_data(test_app_client, wid, bulk_data, local_partition_header)

    if response.status_code != 200:
        assert err in response.json()["detail"]


@pytest.mark.parametrize("welllog_data, bulk_data, err", inconsistent_test_params)
@pytest.mark.anyio
async def test_post_inconsistent_whole_bulk_without_log_curve_family(test_app_client,
                                                                     welllog_data, bulk_data, err,
                                                                     local_partition_header):
    wid = await _create_record(test_app_client, welllog_data, local_partition_header)
    response = await _post_data(test_app_client, wid, bulk_data, local_partition_header)

    if response.status_code != 200:
        assert err in response.json()["detail"]


@pytest.mark.parametrize("welllog_data, bulk_data, err",
                         inconsistent_test_params_column_unmatch_curve_id_and_number_of_columns +
                         inconsistent_test_params)
@pytest.mark.anyio
async def test_post_inconsistent_whole_bulk_with_log_curve_family(test_app_client, welllog_data, bulk_data, err, local_partition_header):
    # because accessing to welllog_data modifies the value for next tests
    my_welllog_data = copy.deepcopy(welllog_data)
    my_welllog_data["Curves"][0]["LogCurveFamilyID"] = "osdu:reference-data--LogCurveFamily:Measured%20Depth:"
    wid = await _create_record(test_app_client, my_welllog_data, local_partition_header)
    response = await _post_data(test_app_client, wid, bulk_data, local_partition_header)

    if response.status_code != 200:
        assert err in response.json()["detail"]


@pytest.mark.parametrize("welllog_data, bulk_data, err", inconsistent_test_params_column_unmatch_curve_id_and_number_of_columns + inconsistent_test_params)
@pytest.mark.anyio
async def test_post_inconsistent_chunk_with_log_curve_family(test_app_client, welllog_data, bulk_data, err, local_partition_header):
    # because accessing to welllog_data modifies the value for next tests
    my_welllog_data = copy.deepcopy(welllog_data)
    my_welllog_data["Curves"][0]["LogCurveFamilyID"] = "osdu:reference-data--LogCurveFamily:Measured%20Depth:"
    wid = await _create_record(test_app_client, my_welllog_data, local_partition_header)
    session_id = await _create_session(test_app_client, wid, local_partition_header)

    response = await _post_chunk(test_app_client, wid, session_id, bulk_data, local_partition_header)
    if response.status_code != 200:
        assert err in response.json()["detail"]

    response = await _commit_session(test_app_client, wid, session_id, local_partition_header)
    if response.status_code != 200:
        assert err in response.json()["detail"] \
               or "no data to commit" in response.json()["detail"]\
               or "reference curve \'MD\' do not cover the entire bulk" in response.json()["detail"]
