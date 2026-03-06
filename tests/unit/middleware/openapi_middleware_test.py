from fastapi import FastAPI, APIRouter
from fastapi.testclient import TestClient
from unittest.mock import patch
import pytest
from app.conf import Config, ConfigurationContainer, cloud_provider_additional_environment
from app.middleware.openapi_middleware import OpenAPIMiddleware, _build_full_server_url

# Dummy router to simulate the openapi.json endpoint
router = APIRouter()


@pytest.fixture(scope="module")
def swagger_full_url_enabled_config():
    config = ConfigurationContainer.with_load_all(environment_dict={
        "OS_WELLBORE_DDMS_DEV_MODE": "True",
        "CLOUD_PROVIDER": "local",
        "SWAGGER_FULL_URL_ENABLED": "true",

    }, contextual_loader=cloud_provider_additional_environment)

    # patching Config in app.conf module, so it is found by other modules
    with patch('app.conf.Config', config):
        yield config


def test_openapi_middleware_loaded_by_env(swagger_full_url_enabled_config):
    """
    Ensure Config.swagger_full_url_enabled is loaded by environment variables and enable OpenAPIMiddleware.
    """
    from importlib import reload
    from app import wdms_app

    reloaded_app = reload(wdms_app)
    assert reloaded_app.wdms_app.user_middleware[-1].cls is OpenAPIMiddleware


def test_build_full_server_url_appends_prefix_when_missing():
    full_url = _build_full_server_url("https://example.org", "/api/os-wellbore-ddms")
    assert full_url == "https://example.org/api/os-wellbore-ddms"


def test_build_full_server_url_does_not_duplicate_prefix():
    full_url = _build_full_server_url("https://example.org/api/os-wellbore-ddms/", "/api/os-wellbore-ddms")
    assert full_url == "https://example.org/api/os-wellbore-ddms"


@pytest.mark.skip("Flaky test, it does not work as expected because of global variable conf.Config. TODO: local config")
def test_openapi_middleware_not_loaded_by_default():
    """
    Ensure CpenAPIMiddleware is not load if Config.swagger_full_url_enabled is set to False.
    """
    from importlib import reload
    from app import wdms_app

    reloaded_app = reload(wdms_app)
    assert OpenAPIMiddleware not in [middleware.cls for middleware in reloaded_app.wdms_app.user_middleware]


@router.get("/api/os-wellbore-ddms/openapi.json")
async def dummy_openapi_endpoint():
    return {"message": "This is a dummy endpoint for testing middleware."}


@pytest.mark.anyio
async def test_openapi_middleware_server_property_update_in_response():
    app = FastAPI()
    app.add_middleware(OpenAPIMiddleware)
    app.include_router(router)

    client = TestClient(app)

    # Make a request to the openapi.json endpoint
    response = client.get('/api/os-wellbore-ddms/openapi.json')
    assert response.status_code == 200
    
    response_json = response.json()
    
    # Test Server domain used by TestClient is "http://testserver"
    expected_url = "http://testserver/api/os-wellbore-ddms"
    assert any(server['url'] == expected_url for server in response_json['servers']), f"Expected servers URL to contain {expected_url}, but got {response_json['servers']}"
