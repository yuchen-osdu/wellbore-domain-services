import pytest
from .fixtures import with_wdms_env
from ..request_builders.wdms.recursive_delete.setup import *
from ..request_builders.wdms.recursive_delete.delete_well import *
from time import sleep
from random import randint


def query_for_record_set_available(env):
    result = build_request_recursive_del_setup_check_state_start().call(env)
    result.assert_ok()
    return result.get_response_obj()


def create_and_set_id(rq, env, env_key):
    rec_id = rq.call(env, assert_status=200).get_response_obj().recordIds[0]
    env.set(env_key, rec_id)


@pytest.fixture
def env_with_records(with_wdms_env):
    """
        There's a bit of logic in this setup. This is because recursive delete relies on search to find
        any children of a record and delete them along the actual record. Given this hierarchy (relation goes
         from child to parent):

            [well] <-- [wellbore] <-- [logset] <-- [log]

        recursively delete the well should delete also the wellbore, logset and log.

        The search result is depended to the indexation to run over the records. Then create the records and immediately
        do the recursive delete won't work. Moreover the there's no way to know when the indexation will be done. So
        the logic here is to create several record set for future runs and if needed wait some time if there's no record
        available yet (up to 10 minutes).

        In order to prevent to parallel test run on the same environment to use the same set of record, we use a single
        record (see build_request_recursive_del_setup_create_record_refs) that references all records
         (well, wellbore, logset, log) involves in the recursive. Successfully delete this single record ensure no
         other run will use the same set of records.
    """

    threshold_enough_record = 6
    number_of_record_to_create = 8
    wait_attempt = 10
    env = with_wdms_env

    check_query_obj = query_for_record_set_available(env)
    nb_record_set = check_query_obj.totalCount
    print(f'{nb_record_set} record set found')

    if nb_record_set < threshold_enough_record:  # not enough record
        print(f'recursive delete setup: Create {number_of_record_to_create} new record set ...')
        # create some records the delete
        for _ in range(number_of_record_to_create):  # chain well->wellbore->logset->logs
            create_and_set_id(build_request_recursive_del_setup_create_well(), env, 'recursive_del_well_id')
            create_and_set_id(build_request_recursive_del_setup_create_wellbore(), env, 'recursive_del_wellbore_id')
            create_and_set_id(build_request_recursive_del_setup_create_logset(), env, 'recursive_del_logset_id')
            create_and_set_id(build_request_recursive_del_setup_create_logs(), env, 'recursive_del_log_id')

            # create the record that references of id for a set of record
            build_request_recursive_del_setup_create_record_refs().call(with_wdms_env).assert_ok()

        # might need to wait
        while nb_record_set < 2 and wait_attempt >= 0:
            print('not enough record indexed => Wait 1 minute ... attempt countdown=' + str(wait_attempt))
            sleep(60)
            check_query_obj = query_for_record_set_available(with_wdms_env)
            nb_record_set = check_query_obj.totalCount
            wait_attempt -= 1

    assert nb_record_set >= 1, 'maximum attempt reached'

    # randomly pick a set of record for the current tests
    while check_query_obj.results:
        idx = randint(0, len(check_query_obj.results)-1)
        selected_set = check_query_obj.results.pop(idx)
        assert selected_set.id
        with_wdms_env.set('recursive_del_ref_record_id', selected_set.id)
        # delete the ref_record to 'reserve' it,
        if build_request_recursive_del_setup_end().call(with_wdms_env).response.status_code == 204:
            # delete response with 204, records successfully reserved
            with with_wdms_env.scoped_update(
                    recursive_del_well_id=selected_set.data.channelNames[0],
                    recursive_del_wellbore_id=selected_set.data.channelNames[1],
                    recursive_del_logset_id=selected_set.data.channelNames[2],
                    recursive_del_log_id=selected_set.data.channelNames[3]):
                yield with_wdms_env

            break

    assert check_query_obj.results, 'fail to select record set for delete recursive tests'


def clean_up_all_ref_record(with_wdms_env):
    for _ in range(10):
        check_query_obj = query_for_record_set_available(with_wdms_env)
        nb_record_set = check_query_obj.totalCount
        for result in check_query_obj.results:
            with_wdms_env.set('recursive_del_ref_record_id', result.id)
            build_request_recursive_del_setup_end().call(with_wdms_env)

        if nb_record_set == len(check_query_obj.results):  # not need for another loop
            break

@pytest.mark.skip(reason="Temporary disable as search indexing is failing, and this block our tests")
@pytest.mark.tag('recursive_delete', 'search')
def test_recursive_delete_well(env_with_records):
    # when
    result = build_request_recursive_delete_well().call(env_with_records)
    result.assert_status_code(204)

    # check children record are gone
    build_request_check_wellbore_is_deleted().call(env_with_records).assert_status_code(404)
    build_request_check_log_is_deleted().call(env_with_records).assert_status_code(404)
    build_request_check_logset_is_deleted().call(env_with_records).assert_status_code(404)
