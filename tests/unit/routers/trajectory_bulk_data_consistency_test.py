import re

import pytest


@pytest.fixture
def dasked_test_app_client(testing_app_local_chunking_with_consistency):
    _, client = testing_app_local_chunking_with_consistency
    return client


async def _create_record(client, data):
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
    response = await client.post("/ddms/v3/wellboretrajectories", json=[record])
    assert response.status_code == 200
    record_id = response.json()["recordIds"][0]
    return record_id


async def _post_data(client, record_id, data):
    return await client.post(
        url=f"/ddms/v3/wellboretrajectories/{record_id}/data",
        json=data,
        headers={"content-type": "application/json"},
    )


async def _create_session(client, record_id):
    response = await client.post(f"/ddms/v3/wellboretrajectories/{record_id}/sessions", json={"mode": "overwrite"})
    assert response.status_code == 200
    session_id = response.json()["id"]
    return session_id


async def _post_chunk(client, record_id, session_id, data):
    response = await client.post(f"/ddms/v3/wellboretrajectories/{record_id}/sessions/{session_id}/data", json=data)
    return response


async def _commit_session(client, record_id, session_id):
    response = await client.patch(
        f"/ddms/v3/wellboretrajectories/{record_id}/sessions/{session_id}", json={"state": "commit"}
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
async def test_consistent_whole_bulk(dasked_test_app_client, traj_data, bulk_data):
    record_id = await _create_record(client=dasked_test_app_client, data=traj_data)
    response = await _post_data(client=dasked_test_app_client, record_id=record_id, data=bulk_data)
    assert response.status_code == 200


@pytest.mark.parametrize("traj_data, bulk_data", test_param)
@pytest.mark.anyio
async def test_post_consistent_chunk(dasked_test_app_client, traj_data, bulk_data):
    wid = await _create_record(dasked_test_app_client, traj_data)
    session_id = await _create_session(dasked_test_app_client, wid)

    response = await _post_chunk(dasked_test_app_client, wid, session_id, bulk_data)
    assert response.status_code == 200

    response = await _commit_session(dasked_test_app_client, wid, session_id)
    assert response.status_code == 200


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
        (
            r"^First value \(0\) of the measured depth is different from TopDepthMeasuredDepth value \(0\.5\) of the"
            r" WellboreTrajectory record\.$"
        ),
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
        (
            r"^Last value \(2\) of the measured depth is different from BaseDepthMeasuredDepth value \(2\.5\) of the"
            r" WellboreTrajectory record\.$"
        ),
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
        (
            r"^Column\(s\) ((\bMD, Incl\b)|(\bIncl, MD\b)) do\(es\) not match any AvailableTrajectoryStationProperties"
            r" name in the WellboreTrajectory record\.$"
        ),
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
        (
            r"^Column\(s\) ((\bMD, Incl\b)|(\bIncl, MD\b)) do\(es\) not match any AvailableTrajectoryStationProperties"
            r" name in the WellboreTrajectory record\.$"
        ),
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
async def test_inconsistent_whole_bulk(dasked_test_app_client, traj_data, bulk_data, expected):
    record_id = await _create_record(dasked_test_app_client, data=traj_data)
    response = await _post_data(dasked_test_app_client, record_id, bulk_data)
    assert response.status_code == 400
    computed = response.json()["detail"]

    pattern = re.compile(expected)
    match = pattern.match(computed)
    assert match, f"{computed} should match regex {expected}"


@pytest.mark.parametrize("traj_data, bulk_data, expected", inconsistent_test_params)
@pytest.mark.anyio
async def test_post_inconsistent_chunk(dasked_test_app_client, traj_data, bulk_data, expected):
    wid = await _create_record(dasked_test_app_client, traj_data)
    session_id = await _create_session(dasked_test_app_client, wid)

    response = await _post_chunk(dasked_test_app_client, wid, session_id, bulk_data)
    assert response.status_code == 200

    response = await _commit_session(dasked_test_app_client, wid, session_id)
    assert response.status_code == 400
    computed = response.json()["detail"]
    pattern = re.compile(expected)
    match = pattern.match(computed)

    assert match, f"{computed} should match regular expression {expected}"
