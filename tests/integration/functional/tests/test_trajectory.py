import pytest
from .fixtures import with_wdms_env

from jsonschema import validate

from wdms_client.request_builders.wdms.crud.trajectory import build_request_create_trajectory_with_id, \
    build_request_get_trajectory, build_request_get_trajectory_bulk_data, build_request_add_trajectory_bulk_data, \
    build_request_create_trajectory, build_request_delete_trajectory


@pytest.mark.tag('trajectory')
@pytest.mark.dependency()
def test_trajectory_error_code(with_wdms_env):
    env = with_wdms_env
    # set data and id variables to use them for the trajectory creation
    env.set('trajectory_data', '{"name":"trajectory_test-trajectory_name"}')
    # create one trajectory and check the response code 200
    resobj = build_request_create_trajectory().call(with_wdms_env, assert_status=200).get_response_obj()
    # set record id variable to use it to get trajectory
    env.set('trajectory_record_id', resobj.recordIds[0])
    # get trajectory and check the response code 200
    build_request_get_trajectory().call(with_wdms_env, assert_status=200)
    # get data trajectory without adding any data to it and check the response code 204
    build_request_get_trajectory_bulk_data().call(with_wdms_env, assert_status=204)
    # Add data to trajectory and check the response code 200
    build_request_add_trajectory_bulk_data().call(with_wdms_env, assert_status=200)
    # get data trajectory and check the response code 200
    build_request_get_trajectory_bulk_data().call(with_wdms_env, assert_status=200)
    # get trajectory and check the response code 200
    resobj=build_request_get_trajectory().call(with_wdms_env, assert_status=200).get_response_obj()
    # set trajectory data json variable to use it to create trajectory with fake bulkURI
    env.set('trajectory_data',
            '{"name":"trajectory_test_CLA_traj-trajectory_name", "bulkURI":"urn:uuid:00000000-0000-0000-0000-000000000000"}')
    # create one trajectory and check the response code 200
    build_request_create_trajectory_with_id().call(with_wdms_env, assert_status=200).get_response_obj()
    # get trajectory and check the response code 500 and the error response message about the invalid bulkURI
    build_request_get_trajectory_bulk_data().call(with_wdms_env, assert_status=500).get_response_obj()
    # delete trajectory
    build_request_delete_trajectory().call(with_wdms_env).assert_status_code(204)
