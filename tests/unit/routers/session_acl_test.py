from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.routers.bulk.bulk_routes import complete_session, post_chunk_data
from app.routers.sessions import UpdateSessionState, UpdateSessionStateValue, delete_session


async def _reject_record(*_args, **_kwargs):
    raise HTTPException(status_code=404, detail="Record not found")


@pytest.mark.anyio
async def test_post_chunk_data_does_not_write_when_record_fetch_fails(monkeypatch):
    monkeypatch.setattr("app.routers.bulk.bulk_routes.fetch_record", _reject_record)
    monkeypatch.setattr("app.routers.bulk.bulk_routes.get_ctx", lambda: object())

    with_session = AsyncMock()
    bulk_io = AsyncMock()
    with pytest.raises(HTTPException):
        await post_chunk_data(
            record_id="record-id",
            session_id=uuid4(),
            request=MagicMock(),
            content_type=MagicMock(),
            with_session=with_session,
            bulk_io=bulk_io,
            df_validation_func=MagicMock(),
        )

    with_session.get_session.assert_not_called()
    bulk_io.write_chunk.assert_not_called()


@pytest.mark.anyio
async def test_abandon_session_does_not_start_when_record_fetch_fails(monkeypatch):
    monkeypatch.setattr("app.routers.bulk.bulk_routes.fetch_record", _reject_record)

    sessions_storage = MagicMock()
    with_session = MagicMock()
    with_session.tenant = MagicMock()
    with_session.sessions_storage = sessions_storage

    with pytest.raises(HTTPException):
        await complete_session(
            record_id="record-id",
            session_id=uuid4(),
            request=MagicMock(),
            ctx=MagicMock(),
            update_request=UpdateSessionState(state=UpdateSessionStateValue.Abandon),
            with_session=with_session,
            bulk_io=AsyncMock(),
            bulk_uri_access=MagicMock(),
            consistency_checks=MagicMock(),
        )

    sessions_storage.initiate_abandon.assert_not_called()


@pytest.mark.anyio
async def test_delete_session_does_not_delete_when_record_fetch_fails(monkeypatch):
    monkeypatch.setattr("app.routers.sessions.fetch_record", _reject_record)

    with_storages = MagicMock()
    with_storages.ctx = MagicMock()
    with_storages.sessions_storage = AsyncMock()

    with pytest.raises(HTTPException):
        await delete_session(
            record_id="record-id",
            session_id=uuid4(),
            request=MagicMock(),
            with_storages=with_storages,
        )

    with_storages.sessions_storage.delete_session.assert_not_called()
