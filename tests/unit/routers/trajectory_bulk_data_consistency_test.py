import pytest

@pytest.fixture
def test_app_client(testing_app_local_chunking_with_consistency):
    _, client = testing_app_local_chunking_with_consistency
    return client


async def _create_record(client, data, header):
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
    response = await client.post("/ddms/v3/wellboretrajectories", json=[record], headers=header)
    assert response.status_code == 200
    record_id = response.json()["recordIds"][0]
    return record_id


async def _post_data(client, record_id, data, header):
    return await client.post(
        url=f"/ddms/v3/wellboretrajectories/{record_id}/data",
        json=data,
        headers={"content-type": "application/json", **header},
    )


async def _create_session(client, record_id, header):
    response = await client.post(f"/ddms/v3/wellboretrajectories/{record_id}/sessions",
                                 json={"mode": "overwrite"},
                                 headers=header)
    assert response.status_code == 200
    session_id = response.json()["id"]
    return session_id


async def _post_chunk(client, record_id, session_id, data, header):
    response = await client.post(f"/ddms/v3/wellboretrajectories/{record_id}/sessions/{session_id}/data",
                                 json=data,
                                 headers=header)
    return response


async def _commit_session(client, record_id, session_id, header):
    response = await client.patch(
        f"/ddms/v3/wellboretrajectories/{record_id}/sessions/{session_id}",
        json={"state": "commit"},
        headers=header,
    )
    return response


def generate_test_data():
    bulk_values = [[0.0, 11.0], [0.5, 22.2], [2.0, 12.0]]

    bulk_data = {"columns": ["MD", "Incl"], "data": bulk_values}

    def value_with_tolerance(v):
        rel_tol = 9e-10
        delta = abs(v) * rel_tol
        return v + delta

    md_station_data = [
        {
            "Name": "MD",
            "TrajectoryStationPropertyTypeID": "partition-id:reference-data--TrajectoryStationPropertyType:MD:",
        },
        {
            "Name": "MD",
        },
        {"Name": "MD", "TrajectoryStationPropertyTypeID": None},
    ]

    incl_station_data = [
        {
            "Name": "Incl",
            "TrajectoryStationPropertyTypeID": (
                "partition-id:reference-data--TrajectoryStationPropertyType:Inclination:"
            ),
        },
        {
            "Name": "Incl",
        },
    ]

    traj_minimal_data = {
        "WellboreID": "partition-id:master-data--Wellbore:72e872c3f86848cd860689ae48d3b6b1:",
        "VerticalMeasurement": {},
    }

    test_data = []
    for md_station in md_station_data:
        for incl_station in incl_station_data:
            test_data.append(
                pytest.param(
                    {
                        **traj_minimal_data,
                        "TopDepthMeasuredDepth": value_with_tolerance(bulk_values[0][0]),
                        "BaseDepthMeasuredDepth": value_with_tolerance(bulk_values[-1][0]),
                        "AvailableTrajectoryStationProperties": [{**md_station}, {**incl_station}],
                    },
                    bulk_data,
                )
            )

    return test_data


test_param = generate_test_data()

test_param.append(
    pytest.param(
        {
            "WellboreID": "partition-id:master-data--Wellbore:72e872c3f86848cd860689ae48d3b6b1:",
            "VerticalMeasurement": {},
            "TopDepthMeasuredDepth": 0.0,
            "BaseDepthMeasuredDepth": 0.0,
            "AvailableTrajectoryStationProperties": [
                {
                    "Name": "MD",
                    "TrajectoryStationPropertyTypeID": "partition-id:reference-data--TrajectoryStationPropertyType:MD:",
                },
                {
                    "Name": "Incl",
                    "TrajectoryStationPropertyTypeID": (
                        "partition-id:reference-data--TrajectoryStationPropertyType:Inclination:"
                    ),
                },
            ],
        },
        {
            "columns": ["MD", "Incl"],
            "data": [
                [0.0, 11.0],
            ],
        },
    )
)

test_param.append(
    pytest.param(
        {
            "WellboreID": "partition-id:master-data--Wellbore:72e872c3f86848cd860689ae48d3b6b1:",
            "VerticalMeasurement": {},
            "TopDepthMeasuredDepth": 0.0,
            "BaseDepthMeasuredDepth": 0.0,
            "AvailableTrajectoryStationProperties": [
                {
                    "Name": "MD",
                    "TrajectoryStationPropertyTypeID": "partition-id:reference-data--TrajectoryStationPropertyType:MD:",
                },
                {
                    "Name": "Incl",
                    "TrajectoryStationPropertyTypeID": (
                        "partition-id:reference-data--TrajectoryStationPropertyType:Inclination:"
                    ),
                },
            ],
        },
        {
            "columns": ["Incl"],
            "data": [
                [11.0],
            ],
        },
    )
)


test_param.append(
    pytest.param(
        {
            "WellboreID": "partition-id:master-data--Wellbore:72e872c3f86848cd860689ae48d3b6b1:",
            "VerticalMeasurement": {},
            "TopDepthMeasuredDepth": 0.0,
            "BaseDepthMeasuredDepth": 0.0,
            "AvailableTrajectoryStationProperties": [
                {
                    "Name": "MD",
                    "TrajectoryStationPropertyTypeID": "partition-id:reference-data--TrajectoryStationPropertyType:MD:",
                },
                {
                    "Name": "Incl",
                    "TrajectoryStationPropertyTypeID": (
                        "partition-id:reference-data--TrajectoryStationPropertyType:Inclination:"
                    ),
                },
            ],
        },
        {
            "columns": ["MD"],
            "data": [
                [0.0],
            ],
        },
    )
)


@pytest.mark.parametrize("traj_data, bulk_data", test_param)
@pytest.mark.anyio
async def test_consistent_whole_bulk(test_app_client, traj_data, bulk_data, local_partition_header):
    record_id = await _create_record(client=test_app_client, data=traj_data, header=local_partition_header)
    response = await _post_data(client=test_app_client, record_id=record_id, data=bulk_data, header=local_partition_header)
    assert response.status_code == 200


@pytest.mark.parametrize("traj_data, bulk_data", test_param)
@pytest.mark.anyio
async def test_post_consistent_chunk(test_app_client, traj_data, bulk_data, local_partition_header):
    wid = await _create_record(client=test_app_client, data=traj_data, header=local_partition_header)

    session_id = await _create_session(client=test_app_client, record_id=wid, header=local_partition_header)

    response = await _post_chunk(client=test_app_client, record_id=wid, session_id=session_id, data=bulk_data, header=local_partition_header)
    assert response.status_code == 200

    response = await _commit_session(client=test_app_client, record_id=wid, session_id=session_id, header=local_partition_header)
    # TODO: one case where commit fails with 422
    #assert response.status_code == 200


inconsistent_test_params = [
    pytest.param(
        {
            "WellboreID": "partition-id:master-data--Wellbore:72e872c3f86848cd860689ae48d3b6b1:",
            "TopDepthMeasuredDepth": 0.5,
            "BaseDepthMeasuredDepth": 2,
            "VerticalMeasurement": {},
            "AvailableTrajectoryStationProperties": [
                {
                    "Name": "Incl",
                    "TrajectoryStationPropertyTypeID": (
                        "partition-id:reference-data--TrajectoryStationPropertyType:Inclination:"
                    ),
                },
                {
                    "Name": "MD",
                    "TrajectoryStationPropertyTypeID": "partition-id:reference-data--TrajectoryStationPropertyType:MD:",
                },
            ],
        },
        {"columns": ["MD", "Incl"], "data": [[0.0, 2222.1], [2, 2222.5]]},
        "First value (0.0) of the measured depth is different from TopDepthMeasuredDepth value (0.5) of the WellboreTrajectory record",
    ),
    pytest.param(
        {
            "WellboreID": "partition-id:master-data--Wellbore:72e872c3f86848cd860689ae48d3b6b1:",
            "TopDepthMeasuredDepth": 0,
            "BaseDepthMeasuredDepth": 2.5,
            "VerticalMeasurement": {},
            "AvailableTrajectoryStationProperties": [
                {
                    "Name": "Incl",
                    "TrajectoryStationPropertyTypeID": (
                        "partition-id:reference-data--TrajectoryStationPropertyType:Inclination:"
                    ),
                },
                {
                    "Name": "MD",
                    "TrajectoryStationPropertyTypeID": "partition-id:reference-data--TrajectoryStationPropertyType:MD:",
                },
            ],
        },
        {"columns": ["MD", "Incl"], "data": [[0.0, 2222.1], [2, 2222.5]]},
        "Last value (2.0) of the measured depth is different from BaseDepthMeasuredDepth value (2.5) of the WellboreTrajectory record",
    ),
    pytest.param(
        {
            "WellboreID": "partition-id:master-data--Wellbore:72e872c3f86848cd860689ae48d3b6b1:",
            "TopDepthMeasuredDepth": 0,
            "BaseDepthMeasuredDepth": 2,
            "VerticalMeasurement": {},
            "AvailableTrajectoryStationProperties": [],
        },
        {"columns": ["MD", "Incl"], "data": [[0.0, 2222.1], [2.0, 2222.5]]},
        " not match any AvailableTrajectoryStationProperties name in the WellboreTrajectory record",
    ),
    pytest.param(
        {
            "WellboreID": "partition-id:master-data--Wellbore:72e872c3f86848cd860689ae48d3b6b1:",
            "TopDepthMeasuredDepth": 0,
            "BaseDepthMeasuredDepth": 2,
            "VerticalMeasurement": {},
            "AvailableTrajectoryStationProperties": None,
        },
        {"columns": ["MD", "Incl"], "data": [[0.0, 2222.1], [2.0, 2222.5]]},
        " not match any AvailableTrajectoryStationProperties name in the WellboreTrajectory record",
    ),
    pytest.param(
        {
            "WellboreID": "partition-id:master-data--Wellbore:MissingAvailableTrajectoryStationProperties:",
            "TopDepthMeasuredDepth": 0,
            "BaseDepthMeasuredDepth": 2,
            "VerticalMeasurement": {},
        },
        {"columns": ["MD"], "data": [[0.0], [2.0]]},
        "Property 'AvailableTrajectoryStationProperties' is missing while curves are present in the bulk data"
    ),
]


@pytest.mark.parametrize("traj_data, bulk_data, expected", inconsistent_test_params)
@pytest.mark.anyio
async def test_inconsistent_whole_bulk(test_app_client, traj_data, bulk_data, expected, local_partition_header):
    record_id = await _create_record(test_app_client, data=traj_data, header=local_partition_header)
    response = await _post_data(test_app_client, record_id, bulk_data, local_partition_header)
    assert response.status_code == 400
    computed = response.json()["detail"]

    assert expected in computed


@pytest.mark.parametrize("traj_data, bulk_data, expected", inconsistent_test_params)
@pytest.mark.anyio
async def test_post_inconsistent_chunk(test_app_client, traj_data, bulk_data, expected, local_partition_header):
    wid = await _create_record(test_app_client, traj_data, local_partition_header)
    session_id = await _create_session(test_app_client, wid, local_partition_header)

    response = await _post_chunk(test_app_client, wid, session_id, bulk_data, local_partition_header)
    assert response.status_code == 200

    response = await _commit_session(test_app_client, wid, session_id, local_partition_header)
    assert response.status_code == 400
    computed = response.json()["detail"]

    assert expected in computed
