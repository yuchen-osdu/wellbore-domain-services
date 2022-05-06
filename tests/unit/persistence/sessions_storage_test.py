# Copyright 2021 Schlumberger
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from datetime import datetime, timedelta

import pytest
from asyncio import sleep
from fastapi import HTTPException
from osdu.core.api.storage.tenant import Tenant
from app.bulk_persistence import (Session,
                                              SessionInternal,
                                              SessionsStorage,
                                              SessionState,
                                              SessionUpdateMode,
                                              SessionNotFound,
                                              SessionInvalidState,
                                              SessionUpdatedEtagUnmatched,
                                              SessionException)
from osdu.core.api.storage.blob_storage_local_fs import LocalFSBlobStorage
from app.context import Context

from tests.unit.test_utils import ctx_fixture


from unittest.mock import patch, PropertyMock


@pytest.fixture
def sessions_storage(ctx_fixture, tmp_path):
    yield SessionsStorage(LocalFSBlobStorage(directory=tmp_path))


@pytest.fixture
def testing_tenant() -> Tenant:
    return Tenant(project_id='p', bucket_name='b', data_partition_id='d')

@pytest.mark.asyncio
@pytest.mark.parametrize("mode, meta, internal", [
    (SessionUpdateMode.Overwrite, {'custom1': 'value1'}, {'internal1': 1337}),
    (SessionUpdateMode.Update, None, None),
    (SessionUpdateMode.Update, {'custom1': 'value1', 'custom2': 'value2'}, 42)])
async def test_session_id(sessions_storage, mode, meta, internal):
    tenant = Tenant(data_partition_id='dp', project_id='prj', bucket_name='bck')
    new_session = await sessions_storage.create_session(tenant, '123', 0, 60,
                                                       mode,
                                                       meta=meta,
                                                       internal=internal)

@pytest.mark.asyncio
@pytest.mark.parametrize("mode, meta, internal", [
    (SessionUpdateMode.Overwrite, {'custom1': 'value1'}, {'internal1': 1337}),
    (SessionUpdateMode.Update, None, None),
    (SessionUpdateMode.Update, {'custom1': 'value1', 'custom2': 'value2'}, 42)])
async def test_create_session(sessions_storage, mode, meta, internal):
    tenant = Tenant(data_partition_id='dp', project_id='prj', bucket_name='bck')
    new_session = await sessions_storage.create_session(tenant, '123', 0, 60,
                                                       mode,
                                                       meta=meta,
                                                       internal=internal)
    assert new_session.session.state == SessionState.Open
    assert new_session.session.id is not None
    assert new_session.session.recordId == '123'
    assert not new_session.session.is_expired
    assert new_session.session.createdTime == new_session.session.updatedTime
    assert new_session.session.meta == meta
    assert new_session.session.mode == mode
    assert new_session.internal == internal


@pytest.mark.asyncio
async def test_session_create_get(sessions_storage, testing_tenant):
    internal_details = {"key_str": "str", "key_int": 123}

    internal_session = await sessions_storage.create_session(
        testing_tenant, '123', 456, 5, SessionUpdateMode.Update,
        internal=internal_details, meta={"custom_key": "custom_value"})
    session = internal_session.session
    assert session.id
    assert session.mode == SessionUpdateMode.Update
    assert session.recordId == '123'
    assert session.state == SessionState.Open
    assert datetime.utcnow() + timedelta(minutes=6) > session.expiry > datetime.utcnow() + timedelta(minutes=4)
    assert internal_session.internal == internal_details
    assert session.meta["custom_key"] == "custom_value"

    session_actual = await sessions_storage.get_session(testing_tenant, '123', session.id)
    assert internal_session == session_actual


@pytest.mark.asyncio
async def test_multiple_session(sessions_storage, testing_tenant):
    s1 = await sessions_storage.create_session(testing_tenant, '123', 456, 5, SessionUpdateMode.Update)
    s2 = await sessions_storage.create_session(testing_tenant, '123', 456, 5, SessionUpdateMode.Update)
    assert s1.session.id != s2.session.id

    session_ids = await sessions_storage.list_sessions(testing_tenant, '123')
    assert str(s1.session.id) in session_ids
    assert str(s2.session.id) in session_ids


@pytest.mark.asyncio
async def test_error_during_commit_should_reset_state(sessions_storage, testing_tenant):

    my_session = await sessions_storage.create_session(testing_tenant, '123', 456, 5, SessionUpdateMode.Update)

    try:
        async with sessions_storage.initiate_commit(testing_tenant, '123', my_session.session.id) as g:
            assert g.session.session.state == SessionState.Committing
            raise RuntimeError("fake")
    except RuntimeError:
        pass

    my_session = await sessions_storage.get_session(testing_tenant, '123', my_session.session.id)
    assert my_session.session.state == SessionState.Open


@pytest.mark.asyncio
async def test_commit_session(sessions_storage, testing_tenant):
    my_session = await sessions_storage.create_session(testing_tenant, '123', 456, 5, SessionUpdateMode.Update)

    async with sessions_storage.initiate_commit(testing_tenant, '123', my_session.session.id) as g:
        assert g.session.session.state == SessionState.Committing

    my_session = await sessions_storage.get_session(testing_tenant, '123', my_session.session.id)
    assert my_session.session.state == SessionState.Committed


@pytest.mark.asyncio
async def test_abandon_session(sessions_storage, testing_tenant):
    my_session = await sessions_storage.create_session(testing_tenant, '123', 456, 5, SessionUpdateMode.Update)

    async with sessions_storage.initiate_abandon(testing_tenant, '123', my_session.session.id) as g:
        assert g.session.session.state == SessionState.Abandoning

    my_session = await sessions_storage.get_session(testing_tenant, '123', my_session.session.id)
    assert my_session.session.state == SessionState.Abandoned


@pytest.mark.asyncio
async def test_error_during_abandon_should_reset_state(sessions_storage, testing_tenant):

    my_session = await sessions_storage.create_session(testing_tenant, '123', 456, 5, SessionUpdateMode.Update)

    try:
        async with sessions_storage.initiate_abandon(testing_tenant, '123', my_session.session.id) as g:
            assert g.session.session.state == SessionState.Abandoning
            raise RuntimeError("fake")
    except RuntimeError:
        pass

    my_session = await sessions_storage.get_session(testing_tenant, '123', my_session.session.id)
    assert my_session.session.state == SessionState.Open


@pytest.mark.asyncio
async def test_update_session(sessions_storage, testing_tenant):
    internal_details = {"key_str": "str", "key_int": 123}

    s1 = await sessions_storage.create_session(
        testing_tenant, '123', 456, 5, SessionUpdateMode.Update,
        internal=internal_details, meta={"custom_key": "custom_value"})

    s1.internal["key_int"] = 567
    s1.session.meta["new_key"] = "foo"

    await sessions_storage.update_session(testing_tenant, s1)
    s2 = await sessions_storage.get_session(testing_tenant, '123', s1.session.id)

    assert s2.internal["key_int"] == 567
    assert s2.session.meta["new_key"] == "foo"

    async with sessions_storage.initiate_commit(testing_tenant, '123', s1.session.id) as g:
        assert g.session.session.state == SessionState.Committing

    s3 = await sessions_storage.get_session(testing_tenant, '123', s1.session.id)
    assert s3.session.state == SessionState.Committed


@pytest.mark.asyncio
async def test_delete_session(sessions_storage, testing_tenant):
    s1 = await sessions_storage.create_session(testing_tenant, '456', 456, 5, SessionUpdateMode.Update)
    s2 = await sessions_storage.create_session(testing_tenant, '456', 456, 5, SessionUpdateMode.Update)

    async with sessions_storage.initiate_abandon(testing_tenant, '456', s1.session.id) as g:
        pass

    await sessions_storage.delete_session(testing_tenant, '456', s1.session.id)

    session_ids = await sessions_storage.list_sessions(testing_tenant, '456')
    assert session_ids == [str(s2.session.id)]



@pytest.mark.asyncio
async def test_get_list_session(sessions_storage):
    tenant = Tenant(data_partition_id='dp', project_id='prj', bucket_name='bck')

    session1 = await sessions_storage.create_session(tenant, '123', 0, 60, SessionUpdateMode.Update)
    session2 = await sessions_storage.create_session(tenant, '123', 0, 60, SessionUpdateMode.Update)
    session3 = await sessions_storage.create_session(tenant, '456', 0, 60, SessionUpdateMode.Update)

    session_actual = await sessions_storage.get_session(tenant, '123', session1.session.id)
    assert session_actual.session == session1.session
    assert session_actual.internal == session1.internal

    session_actual = await sessions_storage.get_session(tenant, '123', session2.session.id)
    assert session_actual.session == session2.session
    assert session_actual.internal == session2.internal

    session_actual = await sessions_storage.get_session(tenant, '456', session3.session.id)
    assert session_actual.session == session3.session
    assert session_actual.internal == session3.internal

    session_list = await sessions_storage.list_sessions(tenant, '123')
    assert set(session_list) == {str(session1.session.id), str(session2.session.id)}

    session_list = await sessions_storage.list_sessions(tenant, '456')
    assert session_list == [str(session3.session.id)]


@pytest.mark.asyncio
async def test_raising_not_found(sessions_storage):
    tenant = Tenant(data_partition_id='dp', project_id='prj', bucket_name='bck')

    existing = await sessions_storage.create_session(tenant, '123', 0, 60, SessionUpdateMode.Update)
    assert await sessions_storage.get_session(tenant, '123', existing.session.id) is not None

    # unknown session id
    with pytest.raises(SessionNotFound):
        await sessions_storage.get_session(tenant, '123', 'unknown')

    # incorrect record id
    with pytest.raises(SessionNotFound):
        await sessions_storage.get_session(tenant, '456', existing.session.id)

    # no session exists for record '456'
    assert await sessions_storage.list_sessions(tenant, '456') == []

    # delete
    await sessions_storage.delete_session(tenant, '123', existing.session.id, force_delete=True)

    # post deletion
    with pytest.raises(SessionNotFound):
        await sessions_storage.get_session(tenant, '123', existing.session.id)


@pytest.mark.asyncio
async def test_update_a_session(sessions_storage):
    tenant = Tenant(data_partition_id='dp', project_id='prj', bucket_name='bck')
    initial = await sessions_storage.create_session(tenant, '123', 0, 60, SessionUpdateMode.Update)
    assert initial.session.meta is None
    assert initial.internal is None

    expected = await sessions_storage.get_session(tenant, initial.session.recordId, initial.session.id)
    expected.session.meta = {"foo": "bar"}
    expected.internal = {"details": {"value": 42}}
    await sleep(0.1)
    await sessions_storage.update_session(tenant, expected)

    actual = await sessions_storage.get_session(tenant, expected.session.recordId, expected.session.id)
    assert actual.session.meta == expected.session.meta
    assert actual.internal == expected.internal
    # created time is same
    assert actual.session.createdTime == expected.session.createdTime

    # updated time is updated
    assert actual.session.updatedTime > initial.session.updatedTime


@pytest.mark.asyncio
@pytest.mark.parametrize("commit, intermediate_state, final_state", [
    (False, SessionState.Abandoning, SessionState.Abandoned),
    (True, SessionState.Committing, SessionState.Committed)])
async def test_complete_session_success(sessions_storage, commit, intermediate_state, final_state):
    tenant = Tenant(data_partition_id='dp', project_id='prj', bucket_name='bck')
    session = await sessions_storage.create_session(tenant, '123', 0, 60, SessionUpdateMode.Update)

    async with sessions_storage.initiate_completion(tenant, session.session.recordId, session.session.id, commit) as g:
        assert g.session is not None
        assert g.session.session.state == intermediate_state

    session = await sessions_storage.get_session(tenant, '123', session.session.id)
    assert session.session.state == final_state


@pytest.mark.asyncio
@pytest.mark.parametrize("commit", [False, True])
@pytest.mark.parametrize("commit2", [False, True])
async def test_cannot_initiate_completion_invalid_state(sessions_storage, commit, commit2):
    tenant = Tenant(data_partition_id='dp', project_id='prj', bucket_name='bck')
    session_internal = await sessions_storage.create_session(tenant, '123', 0, 60, SessionUpdateMode.Update)
    session = session_internal.session

    async with sessions_storage.initiate_completion(tenant, session.recordId, session.id, commit):
        # cannot initiate another completion
        with pytest.raises(SessionInvalidState):
            async with sessions_storage.initiate_completion(tenant, session.recordId, session.id, commit2):
                pass

    # once completed cannot neither
    with pytest.raises(SessionInvalidState):
        async with sessions_storage.initiate_completion(tenant, session.recordId, session.id, commit2):
            pass


@pytest.mark.asyncio
@pytest.mark.parametrize("commit", [False, True])
async def test_in_case_of_failure_should_rollback_state(sessions_storage, commit):
    tenant = Tenant(data_partition_id='dp', project_id='prj', bucket_name='bck')
    session_internal = await sessions_storage.create_session(tenant, '123', 0, 60, SessionUpdateMode.Update)
    session = session_internal.session

    with pytest.raises(ValueError):  # since still want to have the exception raised
        async with sessions_storage.initiate_completion(tenant, session.recordId, session.id, commit):
            raise ValueError("fake")

    # check state is back to 'open'
    actual = await sessions_storage.get_session(tenant, session.recordId, session.id)
    assert actual.session.state == SessionState.Open

    # can commit
    async with sessions_storage.initiate_completion(tenant, session.recordId, session.id, commit):
        pass

    actual = await sessions_storage.get_session(tenant, session.recordId, session.id)
    assert actual.session.is_closed


@pytest.mark.asyncio
async def test_delete_open_session_should_fail(sessions_storage):
    tenant = Tenant(data_partition_id='dp', project_id='prj', bucket_name='bck')
    session_internal = await sessions_storage.create_session(tenant, '123', 0, 60, SessionUpdateMode.Update)

    with pytest.raises(RuntimeError):
        await sessions_storage.delete_session(tenant, '123', session_internal.session.id)


@pytest.mark.asyncio
@pytest.mark.parametrize("commit, final_state", [
    (False, SessionState.Abandoned),
    (True, SessionState.Committed)])
async def test_disaster_case_recovery(sessions_storage, commit, final_state):
    # simulate, disaster while completing (either abandon or commit), like pod crash/killed during completion so that
    # the state is left to abandoning or committing
    tenant = Tenant(data_partition_id='dp', project_id='prj', bucket_name='bck')
    session_internal = await sessions_storage.create_session(tenant, '123', 0, 60, SessionUpdateMode.Update)
    session = session_internal.session

    # change the state to committing
    # here a hackish trick to change the state which is forbidden be pydantic validation rules
    dict_session = session_internal.dict()
    dict_session["session"]["state"] = SessionState.Committing
    updated_session = SessionInternal(**dict_session)
    await sessions_storage.update_session(tenant, updated_session)

    #  check state is committing
    actual = await sessions_storage.get_session(tenant, session.recordId, session.id)
    assert actual.session.state == SessionState.Committing

    # patch session elapsed property to
    with patch.object(Session, 'elapsed_since_update', new_callable=PropertyMock) as elapsed_since_update_mock:
        # given update since only 1 minute
        elapsed_since_update_mock.return_value = 1

        # when try to initiate completion => # then should fail
        with pytest.raises(SessionInvalidState):
            async with sessions_storage.initiate_completion(tenant, session.recordId, session.id, commit=commit):
                pass

        # given update since only 1 hour
        elapsed_since_update_mock.return_value = 3600

        # in that particular state, can initiate a commit or abandon even those it's in committing state
        async with sessions_storage.initiate_completion(tenant, session.recordId, session.id, commit=commit):
            pass

    actual = await sessions_storage.get_session(tenant, session.recordId, session.id)
    assert actual.session.state == final_state


@pytest.mark.asyncio
async def test_http_exception_from_not_found(sessions_storage):
    @SessionsStorage.raise_http_exception
    async def _inner():
        tenant = Tenant(data_partition_id='dp', project_id='prj', bucket_name='bck')
        await sessions_storage.get_session(tenant, '123', '456')

    with pytest.raises(HTTPException) as ex_info:
        await _inner()

    ex = ex_info.value
    assert ex.status_code == 404


@pytest.mark.asyncio
async def test_http_exception_from_invalid_state(sessions_storage):
    @SessionsStorage.raise_http_exception
    async def _inner():
        tenant = Tenant(data_partition_id='dp', project_id='prj', bucket_name='bck')
        s = await sessions_storage.create_session(tenant, '123', 0, 1, SessionUpdateMode.Update)
        async with sessions_storage.initiate_commit(tenant, '123', s.session.id):
            async with sessions_storage.initiate_commit(tenant, '123', s.session.id):
                pass

    with pytest.raises(HTTPException) as ex_info:
        await _inner()

    ex = ex_info.value
    assert ex.status_code == 409


@pytest.mark.asyncio
async def test_http_exception_from_etag_unmatched(sessions_storage):
    @SessionsStorage.raise_http_exception
    async def _inner():
        raise SessionUpdatedEtagUnmatched()

    with pytest.raises(HTTPException) as ex_info:
        await _inner()

    ex = ex_info.value
    assert ex.status_code == 412


@pytest.mark.asyncio
async def test_http_exception_raw(sessions_storage):
    @SessionsStorage.raise_http_exception
    async def _inner():
        raise SessionException()

    with pytest.raises(HTTPException) as ex_info:
        await _inner()

    ex = ex_info.value
    assert ex.status_code == 500







