from datetime import datetime
from enum import Enum
from typing import Dict, Optional, Union, List
from asyncio import gather

from starlette.requests import Request

from app.tenant import resolve_tenant
from app.clients import StorageRecordServiceClient
from app.bulk_persistence import (Session,
                                  SessionInternal,
                                  SessionsStorage,
                                  SessionUpdateMode)
from app.routers.ddms_v3.ddms_v3_utils import DMSV3RouterUtils
from app.routers.record_utils import fetch_record
from app.context import Context
from app.helper.traces import TracingRoute

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from osdu.core.api.storage.blob_storage_base import BlobStorageBase
from pydantic import BaseModel, Field

router = APIRouter(route_class=TracingRoute)


class CreateDataSessionRequest(BaseModel):
    """
    Note:
    if fromVersion is provided, should we:
        force mode to 'update'
        raise an error if mode is overwrite
    """

    fromVersion: int = Field(
        0,
        description='specify the version on top of which update will be applied.'
                    ' By default use the latest one (0). Not relevant if overwrite is set to True.')
    timeToLive: int = Field(
        1440,
        description='optional - time to live in minutes.')

    mode: SessionUpdateMode = Field(
        ...,
        description="merge mode at commit."
                    " If 'update', existing data will be merged with the data sent during the session."
                    " If 'overwrite', existing data will be ignored, the final result will only contains "
                    "data sent within the session.")

    meta: Optional[Dict[str, str]] = Field(
        None,
        description="dictionary all values, stored in the session"
    )


class UpdateSessionStateValue(str, Enum):
    Commit = 'commit',
    Abandon = 'abandon'


class UpdateSessionState(BaseModel):
    state: UpdateSessionStateValue = Field(..., description='`commit` or `abandon` a session')


class UpdateSessionExpiry(BaseModel):
    expiry: datetime = Field(
        ...,
        description='NOT SUPPORTED: extend session lifetime up to the date provided')


class UpdateSessionTimeToLive(BaseModel):
    timeToLive: int = Field(
        ...,
        description='NOT SUPPORTED: time to live in minutes from now, updating session lifetime')


class UpdateSessionRequest(BaseModel):
    __root__: Union[UpdateSessionState, UpdateSessionExpiry, UpdateSessionTimeToLive]


class WithSessionStorages:
    def __init__(self,
                 ctx: Context,
                 tenant,
                 storage: BlobStorageBase,
                 sessions_storage: SessionsStorage,
                 storage_client: StorageRecordServiceClient):
        self.ctx: Context = ctx
        self.tenant = tenant
        self.blob_storage: BlobStorageBase = storage
        self.sessions_storage: SessionsStorage = sessions_storage
        self.storage_service_client: StorageRecordServiceClient = storage_client

    @SessionsStorage.raise_http_exception
    async def get_session(self, record_id: str, session_id: str) -> SessionInternal:
        return await self.sessions_storage.get_session(self.tenant, record_id, session_id)


async def get_session_dependencies():
    ctx = Context.current()
    tenant = await resolve_tenant(ctx.partition_id)
    storage = await ctx.app_injector.get(BlobStorageBase)
    sessions_storage = await ctx.app_injector.get(SessionsStorage)
    storage_client = await ctx.app_injector.get(StorageRecordServiceClient)
    return WithSessionStorages(ctx, tenant, storage, sessions_storage, storage_client)


@router.post(
    "/{record_id}/sessions",
    summary="Create a new session on the given record for writing bulk data.",
    description="Initiate a session based on record version provided. "
                "The session is isolated from any other modifications. "
                "Inside a session, individual chunk doesn't generate new individual version. "
                "A new single version is created only at session completion 'aggregating' all updates."
                " A typical workflow is:"
                "\n1. create a session"
                "\n2. send X chunks (can be parallelized)"
                "\n3. commit the session"
                "\n\nSession has an expiry time."
                " If the session is not completed before, it's automatically dropped. "
                "The session duration is specified in the request but cannot exceeds 24 hours.",
    response_model=Session
)
async def create_session(record_id: str,
                         request: Request,
                         create_rq: CreateDataSessionRequest = None,
                         with_storages: WithSessionStorages = Depends(get_session_dependencies)) -> Session:
    """
    when creating a session:
    check that the record exists
    check that version exists if fromVersion is passed
    The user should be able to passe a record meta data (data.curves) to be patch at the end.
    """
    # fetch latest version
    record = await with_storages.storage_service_client.get_record(record_id, with_storages.ctx.partition_id)
    DMSV3RouterUtils.raise_if_not_osdu_right_entity_kind(record, request.state)
    if create_rq.fromVersion == 0:
        create_rq.fromVersion = record.version
    else:
        # check version exists
        await with_storages.storage_service_client.get_record_version(record_id,
                                                                      create_rq.fromVersion,
                                                                      with_storages.ctx.partition_id)
    internal_session_data = None

    create_rq = create_rq or CreateDataSessionRequest()

    session_internal = await with_storages.sessions_storage.create_session(
        tenant=with_storages.tenant,
        record_id=record_id,
        from_version=create_rq.fromVersion,
        ttl=create_rq.timeToLive,
        mode=create_rq.mode,
        meta=create_rq.meta,
        internal=internal_session_data
    )

    return session_internal.session


@router.get(
    "/{record_id}/sessions/{session_id}",
    summary='get session.',
    response_model=Session
)
async def get_session(record_id: str,
                      session_id: str,
                      request: Request,
                      with_storages: WithSessionStorages = Depends(get_session_dependencies)) -> Session:
    if hasattr(request.state, 'version') and request.state.version != "V2":
        record = await with_storages.storage_service_client.get_record(record_id, with_storages.ctx.partition_id)
        DMSV3RouterUtils.raise_if_not_osdu_right_entity_kind(record, request.state)
    i_session = await with_storages.get_session(record_id, session_id)
    return i_session.session


# TODO remove this once commit/abandon in place, this is only for development purposes
@router.delete(
    "/{record_id}/sessions/{session_id}",
    summary='TEMPORARY: delete session.', status_code=204, response_class=Response,
    include_in_schema=False
)
async def delete_session(record_id: str,
                         session_id: str,
                         with_storages: WithSessionStorages = Depends(get_session_dependencies)):
    force_delete = True
    await with_storages.sessions_storage.delete_session(with_storages.tenant, record_id, session_id, force_delete)


@router.get(
    "/{record_id}/sessions",
    summary='list session of the given record.',
    response_model=List[Session]
)
async def list_session(record_id: str,
                       request: Request,
                       with_storages: WithSessionStorages = Depends(get_session_dependencies)) -> List[Session]:
    if hasattr(request.state, 'version') and request.state.version != "V2":
        record = await with_storages.storage_service_client.get_record(record_id, with_storages.ctx.partition_id)
        DMSV3RouterUtils.raise_if_not_osdu_right_entity_kind(record, request.state)
    session_ids = await with_storages.sessions_storage.list_sessions(with_storages.tenant, record_id)

    get_session_tasks = [
        with_storages.get_session(
            record_id=record_id,
            session_id=session_id) for session_id in session_ids
    ]

    results = await gather(*get_session_tasks)

    return [internal_session.session for internal_session in results]
