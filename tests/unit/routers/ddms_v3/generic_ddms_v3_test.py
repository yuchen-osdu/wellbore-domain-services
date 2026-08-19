import json
import os

from jsonschema.exceptions import ValidationError
from odes_storage.models import CreateUpdateRecordsResponse, Record, RecordVersions
import pytest
from starlette.responses import Response

from app.clients import StorageRecordServiceClient

# Example parameter set, add more as needed
TEST_PARAMS = [
    # (sample_file, record_id, record_version, base_url)
    (
        "PPFGDataset120_unit.json",
        "namespace:work-product-component--PPFGDataset:bb2f4d26-6446-508a-b137-7239ee1bbea1",
        1562066009929332,
        "/ddms/v3/ppfgdataset"
    ),
    (
        "WellPressureTestRawMeasurement_110.json",
        "namespace:work-product-component--WellPressureTestRawMeasurement:0c4b5c5b-32cd-57d2-b6a7-bbff6801fb09",
        1562066009929332,
        "/ddms/v3/wellpressuretestrawmeasurement"
    )
]

@pytest.mark.anyio
@pytest.mark.parametrize("sample_file,record_id,record_version,base_url", TEST_PARAMS)
async def test_get_entity_success(mocker, app_configurable_with_testclient, sample_file, record_id, record_version, base_url):
    dir_path = os.path.dirname(os.path.realpath(__file__))
    with open(os.path.join(dir_path, sample_file), "r", encoding="utf-8") as f:
        record_json = json.load(f)[0]

    expected_response = Record.model_validate(record_json)
    mocked_storage_client = mocker.Mock(spec=StorageRecordServiceClient)
    mocked_storage_client.get_record.return_value = expected_response

    _, client = app_configurable_with_testclient(
        fake_opendes_authorized_user=True,
        fake_data_partition_id=True,
        storage_client_mock=mocked_storage_client
    )
    response = await client.get(url=f"{base_url}/{record_id}",
                                headers={"content-type": "application/json"})

    assert response.status_code == 200
    mocked_storage_client.get_record.assert_called_once()
    get_record_kwargs = mocked_storage_client.get_record.call_args.kwargs
    assert get_record_kwargs["id"] == record_id
    assert get_record_kwargs["data_partition_id"] is None

@pytest.mark.anyio
@pytest.mark.parametrize("sample_file,record_id,record_version,base_url", TEST_PARAMS)
async def test_del_entity_success(mocker, app_configurable_with_testclient, sample_file, record_id, record_version, base_url):
    expected_response = Response()
    mocked_storage_client = mocker.Mock(spec=StorageRecordServiceClient)
    mocked_storage_client.delete_record.return_value = expected_response

    _, client = app_configurable_with_testclient(
        fake_opendes_authorized_user=True,
        fake_data_partition_id=True,
        storage_client_mock=mocked_storage_client
    )
    response = await client.delete(url=f"{base_url}/{record_id}",
                                   headers={"content-type": "application/json"})

    assert response.status_code == 204
    mocked_storage_client.delete_record.assert_called_once_with(id=record_id, data_partition_id=None)


@pytest.mark.anyio
@pytest.mark.parametrize("sample_file,record_id,record_version,base_url", TEST_PARAMS)
async def test_del_entity_with_version_suffix_success(mocker, app_configurable_with_testclient, sample_file, record_id,
                                                      record_version, base_url):
    expected_response = Response()
    mocked_storage_client = mocker.Mock(spec=StorageRecordServiceClient)
    mocked_storage_client.delete_record.return_value = expected_response

    _, client = app_configurable_with_testclient(
        fake_opendes_authorized_user=True,
        fake_data_partition_id=True,
        storage_client_mock=mocked_storage_client
    )
    response = await client.delete(url=f"{base_url}/{record_id}:{record_version}",
                                   headers={"content-type": "application/json"})

    assert response.status_code == 204
    mocked_storage_client.delete_record.assert_called_once_with(id=record_id, data_partition_id=None)

@pytest.mark.anyio
@pytest.mark.parametrize("sample_file,record_id,record_version,base_url", TEST_PARAMS)
async def test_get_entity_versions_success(mocker, app_configurable_with_testclient, sample_file, record_id, record_version, base_url):
    dir_path = os.path.dirname(os.path.realpath(__file__))
    with open(os.path.join(dir_path, sample_file), "r", encoding="utf-8") as f:
        record_json = json.load(f)[0]

    record_versions_data = {
        "recordId": record_id,
        "versions": [record_version]
    }
    expected_response = RecordVersions.model_validate(record_versions_data)
    mocked_storage_client = mocker.Mock(spec=StorageRecordServiceClient)
    mocked_storage_client.get_record.return_value = Record.parse_obj(record_json)
    mocked_storage_client.get_all_record_versions.return_value = expected_response

    _, client = app_configurable_with_testclient(
        fake_opendes_authorized_user=True,
        fake_data_partition_id=True,
        storage_client_mock=mocked_storage_client
    )
    response = await client.get(url=f"{base_url}/{record_id}/versions", headers={"content-type": "application/json"})

    assert response.status_code == 200
    assert response.json() == record_versions_data
    mocked_storage_client.get_all_record_versions.assert_called_once_with(id=record_id, data_partition_id=None)


@pytest.mark.anyio
@pytest.mark.parametrize("sample_file,record_id,record_version,base_url", TEST_PARAMS)
async def test_get_entity_versions_with_version_suffix_success(mocker, app_configurable_with_testclient, sample_file,
                                                               record_id, record_version, base_url):
    dir_path = os.path.dirname(os.path.realpath(__file__))
    with open(os.path.join(dir_path, sample_file), "r", encoding="utf-8") as f:
        record_json = json.load(f)[0]

    record_versions_data = {
        "recordId": record_id,
        "versions": [record_version]
    }
    expected_response = RecordVersions.model_validate(record_versions_data)
    mocked_storage_client = mocker.Mock(spec=StorageRecordServiceClient)
    mocked_storage_client.get_record.return_value = Record.parse_obj(record_json)
    mocked_storage_client.get_all_record_versions.return_value = expected_response

    _, client = app_configurable_with_testclient(
        fake_opendes_authorized_user=True,
        fake_data_partition_id=True,
        storage_client_mock=mocked_storage_client
    )
    response = await client.get(
        url=f"{base_url}/{record_id}:{record_version}/versions",
        headers={"content-type": "application/json"}
    )

    assert response.status_code == 200
    assert response.json() == record_versions_data
    mocked_storage_client.get_record.assert_called_once()
    get_record_kwargs = mocked_storage_client.get_record.call_args.kwargs
    assert get_record_kwargs["id"] == record_id
    assert get_record_kwargs["data_partition_id"] is None
    mocked_storage_client.get_all_record_versions.assert_called_once_with(id=record_id, data_partition_id=None)

@pytest.mark.anyio
@pytest.mark.parametrize("sample_file,record_id,record_version,base_url", TEST_PARAMS)
async def test_get_entity_version_success(mocker, app_configurable_with_testclient, sample_file, record_id, record_version, base_url):
    dir_path = os.path.dirname(os.path.realpath(__file__))
    with open(os.path.join(dir_path, sample_file), "r", encoding="utf-8") as f:
        record_json = json.load(f)[0]

    expected_response = Record.model_validate(record_json)
    mocked_storage_client = mocker.Mock(spec=StorageRecordServiceClient)
    mocked_storage_client.get_record_version.return_value = expected_response

    _, client = app_configurable_with_testclient(
        fake_opendes_authorized_user=True,
        fake_data_partition_id=True,
        storage_client_mock=mocked_storage_client
    )
    response = await client.get(
        url=f"{base_url}/{record_id}/versions/{record_version}",
        headers={"content-type": "application/json"}
    )

    assert response.status_code == 200
    mocked_storage_client.get_record_version.assert_called_once_with(id=record_id, version=record_version, data_partition_id=None)


@pytest.mark.anyio
@pytest.mark.parametrize("sample_file,record_id,record_version,base_url", TEST_PARAMS)
async def test_get_entity_version_with_version_suffix_success(mocker, app_configurable_with_testclient, sample_file,
                                                              record_id, record_version, base_url):
    dir_path = os.path.dirname(os.path.realpath(__file__))
    with open(os.path.join(dir_path, sample_file), "r", encoding="utf-8") as f:
        record_json = json.load(f)[0]

    expected_response = Record.model_validate(record_json)
    mocked_storage_client = mocker.Mock(spec=StorageRecordServiceClient)
    mocked_storage_client.get_record_version.return_value = expected_response

    _, client = app_configurable_with_testclient(
        fake_opendes_authorized_user=True,
        fake_data_partition_id=True,
        storage_client_mock=mocked_storage_client
    )
    response = await client.get(
        url=f"{base_url}/{record_id}:{record_version}/versions/{record_version}",
        headers={"content-type": "application/json"}
    )

    assert response.status_code == 200
    mocked_storage_client.get_record_version.assert_called_once_with(
        id=record_id,
        version=record_version,
        data_partition_id=None
    )

@pytest.mark.anyio
@pytest.mark.parametrize("sample_file,record_id,record_version,base_url", TEST_PARAMS)
async def test_post_entity_success(mocker, app_configurable_with_testclient, sample_file, record_id, record_version, base_url):
    expected_response = CreateUpdateRecordsResponse(
        recordCount=1,
        recordIds=[record_id],
    )
    mocked_storage_client = mocker.Mock(spec=StorageRecordServiceClient)
    mocked_storage_client.create_or_update_records.return_value = expected_response

    dir_path = os.path.dirname(os.path.realpath(__file__))
    with open(os.path.join(dir_path, sample_file), "r", encoding="utf-8") as f:
        record_data = f.read()

    _, client = app_configurable_with_testclient(
        fake_opendes_authorized_user=True,
        fake_data_partition_id=True,
        storage_client_mock=mocked_storage_client
    )
    response = await client.post(url=base_url, data=record_data, headers={"content-type": "application/json"})

    assert response.status_code == 200
    assert mocked_storage_client.create_or_update_records.call_count == 1

@pytest.mark.anyio
@pytest.mark.parametrize("sample_file,record_id,record_version,base_url", TEST_PARAMS)
async def test_post_entity_bad_request_on_validation_error(mocker, app_configurable_with_testclient, sample_file, record_id, record_version, base_url):
    mocked_storage_client = mocker.Mock(spec=StorageRecordServiceClient)
    mocked_schema_library = mocker.patch("app.routers.ddms_v3.generic_ddms_v3.schema_library")
    mocked_schema_library.validate_records.side_effect = ValidationError("Validation Error")

    dir_path = os.path.dirname(os.path.realpath(__file__))
    with open(os.path.join(dir_path, sample_file), "r", encoding="utf-8") as f:
        record_data = f.read()

    _, client = app_configurable_with_testclient(
        fake_opendes_authorized_user=True,
        fake_data_partition_id=True,
        storage_client_mock=mocked_storage_client,
    )
    response = await client.post(url=base_url, data=record_data, headers={"content-type": "application/json"})

    assert response.status_code == 422
    assert mocked_storage_client.create_or_update_records.call_count == 0
