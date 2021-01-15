import pytest
from .fixtures import with_wdms_env
from ..request_builders.wdms.crud.log import *


@pytest.fixture(scope='module')
def env_with_log_record(with_wdms_env):
    #  create the log
    result = build_request_create_log().call(with_wdms_env)
    result.assert_ok()
    resobj = result.get_response_obj()
    assert resobj.recordCount == 1
    assert len(resobj.recordIds) == 1

    with with_wdms_env.scoped_update(log_record_id=resobj.recordIds[0]):
        yield with_wdms_env

        # teardown: delete the log
        build_request_delete_log().call(with_wdms_env).assert_status_code(204)


@pytest.mark.tag('basic', 'crud', 'smoke', 'bulk')
@pytest.mark.dependency()
def test_add_log_bulk_data(env_with_log_record):
    result = build_request_add_log_bulk_data().call(env_with_log_record)
    result.assert_ok()


@pytest.mark.tag('basic', 'crud', 'smoke', 'bulk')
@pytest.mark.dependency(depends=["test_add_log_bulk_data"])
def test_get_log_bulk_data(env_with_log_record):
    result = build_request_get_log_bulk_data().call(env_with_log_record)
    result.assert_ok()

    resobj = result.get_response_obj()
    assert resobj.data[0][1] == 10
    assert resobj.data[1][1] == 20
    assert resobj.data[2][1] == 30
