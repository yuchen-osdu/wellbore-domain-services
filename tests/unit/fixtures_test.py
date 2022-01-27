def test_local_dev_config(local_dev_config):

    # local import
    from app.conf import Config

    # assert config is as expected
    assert local_dev_config.dev_mode.value == True
    assert local_dev_config.cloud_provider.value == "local"

    # asserting config has been patched
    assert Config.dev_mode.value == local_dev_config.dev_mode.value
    assert Config.cloud_provider.value == local_dev_config.cloud_provider.value
    assert (
        Config.service_host_search.value == local_dev_config.service_host_search.value
    )
    assert (
        Config.service_host_storage.value == local_dev_config.service_host_storage.value
    )

    assert Config.modules.value == local_dev_config.modules.value
