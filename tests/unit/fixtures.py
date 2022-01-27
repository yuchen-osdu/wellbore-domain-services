import pytest
from mock import mock


@pytest.fixture(scope="module")
def local_dev_config():
    # local import
    from app.conf import Config

    # set config to a local dev config (assumption for running unit tests)
    Config.dev_mode.value = True
    Config.cloud_provider.value = "local"
    Config.service_host_search.value = "https://test-endpoint/api/search"
    Config.service_host_storage.value = "https://test-endpoint/api/storage"
    Config.modules.value = "log_recognition.routers.log_recognition"
    # This one is necessary as long as we have can_run() in modules dependending on it
    Config.environment_name.value = "evd"

    # patching Config in app.conf module, so it is found by other modules
    with mock.patch("app.conf") as app_conf:
        app_conf.Config = Config

        yield Config
