from unittest.mock import AsyncMock, create_autospec, patch

import odes_schema
from fastapi import  status
from odes_storage.models import CreateUpdateRecordsResponse
import pytest

from app.clients import StorageRecordServiceClient, SchemaServiceClient

storage_record_service_client_mock = create_autospec(StorageRecordServiceClient, spec_set=True, instance=True)
schema_service_client_mock = create_autospec(SchemaServiceClient, spec_set=True, instance=True)


@pytest.fixture
def client(app_configurable_with_testclient, nope_logger_fixture):
    _, client = app_configurable_with_testclient(
        storage_client_mock=storage_record_service_client_mock,
        schema_client_mock=schema_service_client_mock
    )
    return client


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
        ("/ddms/v3/wells", "master-data--Well:1.2.0", {}),
        ("/ddms/v3/wells", "master-data--Well:1.3.0", {}),
        ("/ddms/v3/wellbores", "master-data--Wellbore:1.0.0", {}),
        ("/ddms/v3/wellbores", "master-data--Wellbore:1.1.0", {}),
        ("/ddms/v3/wellbores", "master-data--Wellbore:1.1.1", {}),
        ("/ddms/v3/wellbores", "master-data--Wellbore:1.2.0", {}),
        ("/ddms/v3/wellbores", "master-data--Wellbore:1.3.0", {}),
        ("/ddms/v3/wellbores", "master-data--Wellbore:1.4.0", {}),
        ("/ddms/v3/welllogs", "work-product-component--WellLog:1.0.0", {}),
        ("/ddms/v3/welllogs", "work-product-component--WellLog:1.1.0", {}),
        ("/ddms/v3/welllogs", "work-product-component--WellLog:1.0.0", {"TopMeasuredDepth": 10}),
        ("/ddms/v3/welllogs", "work-product-component--WellLog:1.1.0", {"TopMeasuredDepth": 10, "SamplingStart": 10}),
        ("/ddms/v3/welllogs", "work-product-component--WellLog:1.2.0", {"TopMeasuredDepth": 10, "SamplingStart": 10}),
        ("/ddms/v3/welllogs", "work-product-component--WellLog:1.3.0", {"TopMeasuredDepth": 10, "SamplingStart": 10}),
        ("/ddms/v3/welllogs", "work-product-component--WellLog:1.4.0", {"TopMeasuredDepth": 10, "SamplingStart": 10}),
        ("/ddms/v3/wellboremarkersets", "work-product-component--WellboreMarkerSet:1.0.0", {}),
        ("/ddms/v3/wellboremarkersets", "work-product-component--WellboreMarkerSet:1.2.0", {}),
        ("/ddms/v3/wellboremarkersets", "work-product-component--WellboreMarkerSet:1.2.1", {}),
        ("/ddms/v3/wellboremarkersets", "work-product-component--WellboreMarkerSet:1.3.0", {}),
        ("/ddms/v3/wellboremarkersets", "work-product-component--WellboreMarkerSet:1.1.0", {   "AvailableMarkerProperties": [
                    {
                        "MarkerPropertyTypeID": "partition-id:reference-data--MarkerPropertyType:MissingThickness:",
                        "MarkerPropertyUnitID": "partition-id:reference-data--UnitOfMeasure:ft:",
                        "Name": "MissingThickness"
                    }]}),
        ("/ddms/v3/wellboremarkersets", "work-product-component--WellboreMarkerSet:1.4.0", {}),
        ("/ddms/v3/wellboreintervalsets", "work-product-component--WellboreIntervalSet:1.0.0", {}),
        ("/ddms/v3/wellboreintervalsets", "work-product-component--WellboreIntervalSet:1.1.0", {}),
        ("/ddms/v3/wellboreintervalsets", "work-product-component--WellboreIntervalSet:1.2.0", {}),
        ("/ddms/v3/wellboretrajectories", "work-product-component--WellboreTrajectory:1.0.0", trajectory_data),
        ("/ddms/v3/wellboretrajectories", "work-product-component--WellboreTrajectory:1.1.0", trajectory_data),
        ("/ddms/v3/wellboretrajectories", "work-product-component--WellboreTrajectory:1.2.0", trajectory_data),
        ("/ddms/v3/wellboretrajectories", "work-product-component--WellboreTrajectory:1.3.0", trajectory_data),
        ("/ddms/v3/welllogacquisition", "master-data--WellLogAcquisition:1.0.0", {}),
        ("/ddms/v3/ppfgdataset", "work-product-component--PPFGDataset:1.2.0", {}),
    ],
)
@pytest.mark.anyio
async def test_check_supported_kind(mocker, client, api, record_type, data):
    mocker.patch.object(
        storage_record_service_client_mock,
        "create_or_update_records",
        AsyncMock(
            return_value=CreateUpdateRecordsResponse(recordCount=1, recordIds=["rec1"])
        ),
    )
    response = await client.post(
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
    "api, record_type, data, code",
    [
        ("/ddms/v3/wells", "master-data--foo:1.0.0", {}, 404),
        ("/ddms/v3/wells", "master-data--Well:1.0.1", {}, 404),
        ("/ddms/v3/wells", "master-data--Wellbore:1.0.0", {}, 422),
        ("/ddms/v3/wells", "master-data--Well:2.0.0", {}, 404),
        ("/ddms/v3/wellbores", "master-data--foo:1.0.0", {}, 404),
        ("/ddms/v3/wellbores", "master-data--Wellbore:1.0.1", {}, 404),
        ("/ddms/v3/wellbores", "master-data--Wellbore:2.0.0", {}, 404),
        ("/ddms/v3/welllogs", "work-product-component--foo:1.0.0", {}, 404),
        ("/ddms/v3/welllogs", "work-product-component--WellLog:1.0.1", {}, 404),
        ("/ddms/v3/welllogs", "work-product-component--WellLog:2.0.0", {}, 404),
        ("/ddms/v3/wellbores", "master-data--foo:1.0.0", {}, 404),
        ("/ddms/v3/wellbores", "master-data--Wellbore:1.0.1", {}, 404),
        ("/ddms/v3/wellbores", "master-data--Wellbore:2.0.0", {}, 404),
        ("/ddms/v3/wellboremarkersets", "work-product-component--foo:1.0.0", {}, 404),
        ("/ddms/v3/wellboremarkersets", "work-product-component--WellboreMarkerSet:1.0.1", {}, 404),
        ("/ddms/v3/wellboremarkersets", "work-product-component--WellboreMarkerSet:2.0.0", {}, 404),
        ("/ddms/v3/wellboreintervalsets", "work-product-component--WellboreIntervalSet:1.0.1", {}, 404),
        ("/ddms/v3/wellboretrajectories", "work-product-component--foo:1.0.0", trajectory_data, 404),
        ("/ddms/v3/wellboretrajectories", "work-product-component--WellboreTrajectory:1.0.1", trajectory_data, 404),
        ("/ddms/v3/wellboretrajectories", "work-product-component--WellboreTrajectory:2.0.0", trajectory_data, 404),
        ("/ddms/v3/welllogacquisition", "master-data--WellLogAcquisition:1.0.1", {}, 404),
    ],
)
@pytest.mark.anyio
async def test_check_not_supported_kind(mocker, client, api, record_type, data, code):
    mocker.patch.object(
        schema_service_client_mock,
        "get_schema",
        AsyncMock(
            side_effect=odes_schema.UnexpectedResponse(
                status_code=404,
                reason_phrase="Item not found",
                content="".encode(encoding="utf-8"),
                headers=None,
            )
        ),
    )

    response = await client.post(
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
    assert response.status_code == code


@pytest.mark.anyio
async def test_invalid_welllog_schema(client):
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
            "data": {"TopMeasuredDepth": 10},
        },
        {
            "kind": "osdu:wks:work-product-component--WellLog:1.0.0",
            "legal": {"legaltags": ["foo"], "otherRelevantDataCountries": ["FR"]},
            "acl": {"owners": ["foo@bar.com"], "viewers": ["foo@bar.com"]},
            "data": {"ReferenceCurveID": "foo"},
        },
    ]

    response = await client.post(url="/ddms/v3/welllogs", json=json, headers={"content-type": "application/json"})
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY  # With jsonschema check the actual schema
    # is tested and 422 is returned instead of 400
    assert "Unevaluated properties are not allowed ('ReferenceCurveID' was unexpected)" in response.json().get(
        "errors")


@pytest.mark.anyio
async def test_invalid_markerset_schema(client):
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
    response = await client.post(url="/ddms/v3/wellboremarkersets", json=json , headers={"content-type": "application/json"})
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert "Unevaluated properties are not allowed ('AvailableMarkerProperties' was unexpected)" in response.json().get(
        "errors"
    )


@pytest.mark.anyio
async def test_invalid_trajectory_schema(client):
    json = [
        {
            "kind": "osdu:wks:work-product-component--WellboreTrajectory:1.0.0",
            "legal": {"legaltags": ["foo"], "otherRelevantDataCountries": ["FR"]},
            "acl": {"owners": ["foo@bar.com"], "viewers": ["foo@bar.com"]},
            "data": {
                "WellboreID":"namespace:master-data--Wellbore:c7c421a7-f496-5aef-8093-298c32bfdea9:456",
                "TopDepthMeasuredDepth": 10,
                "BaseDepthMeasuredDepth": 10,
                "VerticalMeasurement": {},
                "AppliedOperations":["op1", "op2"]
            }
        },

    ]
    response = await client.post(url="/ddms/v3/wellboretrajectories", json=json , headers={"content-type": "application/json"})
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert "Unevaluated properties are not allowed ('AppliedOperations' was unexpected)" in response.json().get(
        "errors"
    )
