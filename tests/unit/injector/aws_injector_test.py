from osdu.core.api.storage.blob_storage_base import BlobStorageBase
from osdu_aws.storage.storage_aws import AwsStorage
from app.injector.aws_injector import AwsInjector
from app.injector.app_injector import AppInjector
from unittest.mock import MagicMock, patch
import pytest

@pytest.fixture
def app_injector():
    return MagicMock()

@pytest.fixture
def aws_storage():
    return MagicMock()

@pytest.fixture
def ctx():
    context = MagicMock()
    context.partition_id = 'some_partition_id'
    return context

@pytest.fixture
def tenant():
    return MagicMock()

def test_configure():
    app_injector = MagicMock(spec=AppInjector)
    
    injector = AwsInjector()
    injector.configure(app_injector)
    
    assert app_injector.register.call_count == 1

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
