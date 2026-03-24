import pytest
import allure

from wdms_client.request_builders import make_base_request_proto
from wdms_client.request_runner import RequestRunner
from .fixtures import with_wdms_env


@allure.feature('Wellbore DMS API')
@allure.story('Log Recognition')
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.tag('smoke', 'log_recognition')
def test_basic_log_recognition(with_wdms_env):
    result = RequestRunner(make_base_request_proto('POST', '/log-recognition/family', payload={
        "label": "GRD",
        "log_unit": "GAPI",
        "description": "LDTD Gamma Ray"
    })).call(with_wdms_env)
    result.assert_ok()

    resobj = result.get_response_obj()
    assert resobj["family"] == "Gamma Ray"
    assert resobj["log_unit"] == "GAPI"
    assert resobj["base_unit"] == "gAPI"
