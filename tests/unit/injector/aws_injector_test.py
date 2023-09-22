from app.bulk_persistence import (
    BulkPersistenceConfig,
    DaskBulkStorage
)
from osdu.core.api.storage.blob_storage_base import BlobStorageBase
from osdu_aws.storage.storage_aws import AwsStorage
from app.injector.aws_injector import AwsInjector
from app.injector.app_injector import AppInjector
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

@pytest.fixture
def app_injector():
    return MagicMock()

@pytest.fixture
def aws_storage():
    return MagicMock()

@pytest.fixture
def dask_bulk_storage():
    return MagicMock()

@pytest.fixture
def ctx():
    context = MagicMock()
    context.partition_id = 'some_partition_id'
    return context

@pytest.fixture
def tenant():
    return MagicMock()

@patch("app.injector.aws_injector.get_config", return_value=MagicMock(spec=BulkPersistenceConfig))
def test_configure(mock_get_config):
    app_injector = MagicMock(spec=AppInjector)
    
    injector = AwsInjector()
    injector.configure(app_injector)
    
    assert app_injector.register.call_count == 2

@pytest.mark.anyio
async def test_build_aws_storage():
    mock_config = MagicMock()
    mock_config.aws_region.value = "us-east-1" 
    mock_config.aws_env.value = "mocked_env"
    mock_ssm_client = MagicMock()
    mock_sts_client = MagicMock()
    
    mock_ssm_client.get_parameter.return_value = {'Parameter': {'Value': 'mock-value'}}
    mock_sts_client.get_caller_identity.return_value = {'Arn': 'mock-arn'}

    with patch.object(AwsStorage, "__init__", lambda x, *args, **kwargs: None):
        with patch("boto3.client") as mock_boto_client:

            def client_side_effect(service, *args, **kwargs):
                return mock_ssm_client if service == 'ssm' else mock_sts_client

            mock_boto_client.side_effect = client_side_effect

            with patch("app.injector.aws_injector.Config", mock_config):
                result = await AwsInjector.build_aws_storage()

    assert isinstance(result, BlobStorageBase)
    

@pytest.mark.anyio
@patch("app.injector.aws_injector.Config")
@patch("app.injector.aws_injector.Context")
@patch("app.injector.aws_injector.resolve_tenant")
@patch("app.injector.aws_injector.aws_parameters")
@patch("app.injector.aws_injector.DaskBulkStorage.create")
async def test_build_aws_dask_blob_storage(mock_create, mock_aws_parameters, mock_resolve_tenant, mock_Context, mock_Config):
    mock_Config.aws_region.value = "mocked_region"
    mock_Config.aws_env.value = "mocked_env"

    mock_ctx = MagicMock()
    mock_ctx.partition_id = "mocked_partition_id"
    mock_Context.current.return_value = mock_ctx

    mock_resolve_tenant.return_value = AsyncMock(return_value="mocked_tenant")
    mock_aws_parameters.return_value = AsyncMock(return_value="mocked_parameters")

    mock_app_injector = MagicMock()
    mock_app_injector.get = AsyncMock(return_value="mocked_dask_client")

    mock_dask_storage_instance = MagicMock()
    mock_create.return_value = mock_dask_storage_instance

    result = await AwsInjector.build_aws_dask_blob_storage(mock_app_injector, "mocked_bulk_config")

    assert result == mock_dask_storage_instance
    assert hasattr(result, '_fs')