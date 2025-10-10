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
import uuid
from typing import Dict, Optional, List, Any
from enum import Enum
from asyncio import gather
from uuid import UUID

from pydantic import ConfigDict, BaseModel, Field
from fastapi import status, HTTPException
from datetime import datetime, timedelta, timezone
from osdu.core.api.storage.blob_storage_base import BlobStorageBase
from osdu.core.api.storage.tenant import Tenant
from osdu.core.api.storage.exceptions import PreconditionFailedException, ResourceNotFoundException

from .capture_timings import capture_timings
from app.helper.logger import get_logger
from app.helper.traces_ot import get_tracer
_tracer = get_tracer()


class SessionState(str, Enum):
    Open = 'open',
    Committing = 'committing',
    Abandoning = 'abandoning',
    Committed = 'committed',
    Abandoned = 'abandoned'


class SessionUpdateMode(str, Enum):
    Overwrite = 'overwrite'
    Update = 'update'


class Session(BaseModel):
    """ model of session exposed  """

    id: UUID = Field(..., description="identifier of the current session.",
                          frozen=True)
    recordId: str = Field(..., description="identifier of the record of which the session is attached to.",
                          frozen=True)
    fromVersion: int = Field(..., description="record version on top of which the session is based.",
                             frozen=True)
    mode: SessionUpdateMode = Field(
        ...,
        description="merge mode at commit."
                    " If 'update', existing data will be merged with the data sent during the session."
                    " If 'overrride', existing data will be ignored, the final result will only contains "
                    "data sent within the session.",
        frozen=True)
    expiry: datetime = Field(
        ...,
        description="If the session is not committed before this dead line, session is automatically abandoned.")
    createdTime: datetime = Field(..., description="creation date", frozen=True)
    updatedTime: datetime = Field(..., description="updated date")
    state: SessionState = Field(..., frozen=True)
    meta: Optional[Dict[str, str]] = Field(
        None,
        description="miscellaneous metadata associated to the session. The session creator can set some data here.")
    model_config = ConfigDict(validate_assignment=True, json_schema_extra={
        "example": {
            "id": "xx1234",
            "recordId": "opendes:log:991234",
            "fromVersion": 25686567113,
            "mode": "update",
            "createdTime": "2021-03-07T15:49:01+00:00",
            "updatedTime": "2021-03-07T15:58:01+00:00",
            "expiry": "2021-03-08T15:49:01+00:00",
            "state": "open",
            "meta": {
                "creatorCustom": "someValue"
            }
        }
    })

    @property
    def is_expired(self) -> bool:
        return datetime.now(timezone.utc) > self.expiry

    @property
    def is_closed(self) -> bool:
        return self.state == SessionState.Committed or self.state == SessionState.Abandoned

    @property
    def elapsed_since_update(self) -> float:
        return (datetime.now(timezone.utc) - self.updatedTime).total_seconds()

    def set_meta_value(self, key: str, value: str):
        if self.meta is None:
            self.meta = {key: value}
        else:
            self.meta[key] = value

    def get_meta_value(self, key: str, default: Optional[str] = None) -> Optional[str]:
        if self.meta is None:
            return default
        return self.meta.get(key, default)


class CommitSessionResponse(Session):
    model_config = ConfigDict(validate_assignment=True, json_schema_extra={
        "example": {
            **Session.model_config["json_schema_extra"]["example"],
            "version": 123456789,
        }
    })

    version: Optional[int] = Field(
        None,
        description='Record version in case of successful commit',
        examples=[1562066009929332],
        title='Version Number',
    )


class SessionInternal(BaseModel):
    session: Session
    etag: Optional[str] = Field(None, frozen=True)  # internal only, read only
    internal: Optional[Any] = Field(
        None,
        description="contains internal not expected to be exposed."
                    "TODO see if it's needed, a potential usage could be to keep track to chunk details,"
                    " for 'quick' check validation. If not needed to be remove, this is mainly to support "
                    "our current exploratory work.")
    model_config = ConfigDict(validate_assignment=True)


class SessionException(Exception):
    def __init__(self, record_id: str = None,
                 session_id: UUID = None,
                 message: str = None,
                 http_status_equivalent=status.HTTP_500_INTERNAL_SERVER_ERROR):
        super().__init__(f'Error on session {str(session_id)} for record {record_id}: {message or "unknown"}')
        self.record_id = record_id
        self.session_id = session_id
        self.http_status = http_status_equivalent

    def raise_as_http(self):
        raise HTTPException(
            status_code=self.http_status,
            detail=str(self))


class SessionUpdatedEtagUnmatched(SessionException):
    def __init__(self, record_id: str = None, session_id: UUID = None, message=None):
        super().__init__(record_id,
                         session_id,
                         message or "cannot update because precondition failed.",
                         status.HTTP_412_PRECONDITION_FAILED)


class SessionInvalidState(SessionException):
    def __init__(self, record_id: str = None, session_id: UUID = None, message=None):
        super().__init__(record_id,
                         session_id,
                         message or "invalid state, session is no longer 'Opened'.",
                         status.HTTP_409_CONFLICT)


class SessionNotFound(SessionException):
    def __init__(self, record_id: str = None, session_id: UUID = None, message=None):
        super().__init__(record_id,
                         session_id,
                         message or "not found.",
                         status.HTTP_404_NOT_FOUND)


class SessionsStorage:
    """
    This client do session persistence on top of a blob storage
    """

    def __init__(self, blob_storage: BlobStorageBase):
        self._storage = blob_storage

    @staticmethod
    def _build_session_complete_name(record_id: str, session_id: UUID):
        return f'sessions/{record_id}/{str(session_id)}'

    @_tracer.start_as_current_span('blob_storage_upload_session')
    async def _store_session(self, tenant: Tenant, session: SessionInternal) -> SessionInternal:
        etag = session.etag
        if etag is not None:  # this differentiate creation (etag is None) versus update (etag not None)
            session.session.updatedTime = datetime.now(timezone.utc)
        content = session.model_dump_json(exclude={'etag'})  # etag must not be persisted

        try:
            blob = await self._storage.upload(
                tenant,
                self._build_session_complete_name(session.session.recordId, session.session.id),
                content,
                content_type="application/json",
                if_match=etag)
        except PreconditionFailedException:
            raise SessionUpdatedEtagUnmatched(session.session.recordId, session.session.id)

        return SessionInternal(session=session.session,
                               etag=blob.etag,
                               internal=session.internal)  # returned the updated session

    @_tracer.start_as_current_span('blob_storage_get_session')
    async def _get_session(self, tenant: Tenant, record_id: str, session_id: UUID) -> SessionInternal:
        object_name = self._build_session_complete_name(record_id, session_id)

        try:
            blob_meta, blob_content = await gather(
                self._storage.download_metadata(tenant, object_name),
                self._storage.download(tenant, object_name)
            )

            session_without_etag = SessionInternal.model_validate_json(blob_content)

            return SessionInternal(session=session_without_etag.session,
                                   etag=blob_meta.etag,
                                   internal=session_without_etag.internal)

        except ResourceNotFoundException:
            raise SessionNotFound(record_id, session_id)

    @staticmethod
    def raise_http_exception(func):
        async def inner(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except SessionException as ex:
                ex.raise_as_http()

        return inner

    @capture_timings('create_session')
    async def create_session(self, tenant: Tenant, record_id: str, from_version: int, ttl: int, mode: SessionUpdateMode,
                             *,
                             meta: Optional[Dict[str, str]] = None, internal: Optional[Any] = None) -> SessionInternal:
        utc_now = datetime.now(timezone.utc)
        session = Session(id=uuid.uuid4(), fromVersion=from_version, recordId=record_id, mode=mode,
                          createdTime=utc_now, updatedTime=utc_now, expiry=utc_now + timedelta(minutes=ttl),
                          state=SessionState.Open, meta=meta)

        internal = SessionInternal(session=session, internal=internal)
        return await self._store_session(tenant, internal)

    @capture_timings('get_session')
    async def get_session(self, tenant: Tenant, record_id: str, session_id: UUID) -> Optional[SessionInternal]:
        return await self._get_session(tenant, record_id, session_id)

    async def list_sessions(self, tenant: Tenant, record_id: str) -> List[str]:
        prefix = self._build_session_complete_name(record_id, '')
        names = await self._storage.list_objects(tenant, prefix=prefix)
        return [name.split('/')[-1] for name in names]

    async def delete_session(self, tenant: Tenant, record_id: str, session_id: UUID, force_delete=False):
        """ delete a session. If force_delete is not True it will raise a runtime exception is session is not
        close (i.e. state not abandoned nor committed)"""
        internal = await self._get_session(tenant, record_id, session_id)

        if not internal.session.is_closed:
            get_logger().error(f"Invalid state for session deletion: {internal.session}")
            if not force_delete:
                raise RuntimeError("Session cannot be deleted. "
                                   "Invalid state. The session must be completed or abandoned before")

        object_name = self._build_session_complete_name(record_id, session_id)
        await self._storage.delete(tenant, object_name)
        get_logger().debug(f'session deleted: {internal.session}')

    class CompletionContextManager:
        def __init__(self, client: 'SessionsStorage', tenant: Tenant, record_id: str, session_id: UUID, commit: bool):
            self._tenant = tenant
            self._client = client
            self._record_id = record_id
            self._session_id = session_id
            self.commit = commit
            self._is_armed = None
            self.session: SessionInternal = None

        async def __aenter__(self):
            # on enter set to Committing or Abandoning
            new_state = SessionState.Committing if self.commit else SessionState.Abandoning
            self.session = await self._client._update_session_state(
                self._tenant, self._record_id, self._session_id, new_state)
            self._is_armed = True
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            if not self._is_armed:
                return

            if exc_type is None:
                #  success case
                new_state = SessionState.Committed if self.commit else SessionState.Abandoned
                force_update = False
            else:
                #  failure case
                new_state = SessionState.Open
                force_update = True

            self.session = await self._client._update_session_state(self._tenant,
                                                                    self._record_id,
                                                                    self._session_id,
                                                                    new_state, force_update=force_update)
            self._is_armed = False

    def initiate_commit(self, tenant: Tenant, record_id: str, session_id: UUID) -> CompletionContextManager:
        """ must be used in async context:
        ```
            async with sessions_storage.initiate_commit(...) as guard:
                 # some work
        ``` """
        return self.CompletionContextManager(self, tenant, record_id, session_id, commit=True)

    def initiate_abandon(self, tenant: Tenant, record_id: str, session_id: UUID) -> CompletionContextManager:
        """ must be used in async context:
        ```
            async with sessions_storage.initiate_abandon(...) as guard:
                 # some work
        ``` """
        return self.CompletionContextManager(self, tenant, record_id, session_id, commit=False)

    def initiate_completion(self, tenant: Tenant, record_id: str,
                            session_id: UUID, commit: bool) -> CompletionContextManager:
        """ initiate completion, with commit = True is equivalent to `initiate_commit`,
         with commit = False is equivalent to `initiate_abandon`"""
        return self.CompletionContextManager(self, tenant, record_id, session_id, commit=commit)

    async def _update_session_state(self,
                                    tenant: Tenant,
                                    record_id: str,
                                    session_id: UUID,
                                    new_state: SessionState, *, force_update: bool = False) -> SessionInternal:
        """ State update possibility matrix
| actual / requested => | open | committing               | committed | abandoning               | abandoned |
|-----------------------|------|--------------------------|-----------|--------------------------|-----------|
| open                  | X    | OK                       | X         | OK                       | X         |
| committing            | X    | only if timeout detected | OK        | only if timeout detected | X         |
| committed             | X    | X                        | X         | X                        | X         |
| abandoning            | X    | X                        | X         | only if timeout detected | OK        |
| abandoned             | X    | X                        | X         | X                        | X         |

        """
        i_session = await self._get_session(tenant, record_id, session_id)

        if not force_update:
            assert new_state != SessionState.Open

            # check for state if new can be applied
            if i_session.session.is_closed:
                raise SessionInvalidState(record_id, session_id, "session already closed")

            if new_state == SessionState.Committed:
                assert i_session.session.state == SessionState.Committing, \
                    f"{SessionState.Committed.value} can only be applied on {SessionState.Committing.value}"

            elif new_state == SessionState.Abandoned:
                assert i_session.session.state == SessionState.Abandoning, \
                    f"{SessionState.Abandoned.value} can only be applied on {SessionState.Abandoning.value}"
            elif i_session.session.state != SessionState.Open:
                # if here means both actual and requested state are either 'committing' or 'abandoning'
                # this is not allowed unless we detected long inactivity (5 minutes). So in order to not stay in these
                # state forever in case of unexpected error/crash, we allow to continue
                if i_session.session.elapsed_since_update < 5. * 60.:
                    raise SessionInvalidState(record_id, session_id,
                                              f"session is already {i_session.session.state.value}")

                # by the way we forbid to try to commit a session always in abandoning status
                if new_state == SessionState.Committing and i_session.session.state == SessionState.Abandoning:
                    raise SessionInvalidState(record_id, session_id,
                                              f"session cannot be {SessionState.Committing.value}")

                # let's continue and finish the session
                get_logger().warning(
                    f"session {i_session.session.id} for record {i_session.session.recordId} "
                    f"appears idle in state {i_session.session.state} since {i_session.session.updatedTime}."
                    f" State update allowed, will be {new_state}"
                )

        dict_session = i_session.model_dump()
        dict_session["session"]["state"] = new_state
        updated = SessionInternal(**dict_session)
        # if session has been updated meanwhile, this call will fail and raise SessionUpdatedEtagUnmatched
        return await self._store_session(tenant, updated)

    async def update_session(self, tenant: Tenant, session: SessionInternal) -> SessionInternal:
        """ for internal only, not for state update """
        return await self._store_session(tenant, session)

