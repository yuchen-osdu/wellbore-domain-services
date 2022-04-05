import pytest


@pytest.mark.parametrize("probe_path", ['/readiness', '/healthz', '/'])
def test_probe_request(app_configurable_with_testclient, probe_path, nope_logger_fixture):
    app, client_after_startup = app_configurable_with_testclient()

    response = client_after_startup.get(probe_path)
    response_json = response.json()
    assert response.status_code == 200
    assert response_json == {'status': 'healthy'}

    nope_logger_fixture.info.assert_not_called()
