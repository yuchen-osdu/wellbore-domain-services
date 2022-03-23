import pytest
from unittest.mock import AsyncMock
from unittest.mock import patch, mock_open
from contextlib import suppress

from tests.unit.test_utils import side_effect_raise


from dask.distributed import Client
from app.bulk_persistence.dask.dask_data_ipc import DaskNoneDataIPC, DaskLocalFileDataIPC, DaskNativeDataIPC


async def data_async_gen(data=b"123456789", chunk_size=3):
    for i in range(0, len(data), chunk_size):
        yield data[i:i + chunk_size]


async def assert_ipc_forward_equal(ipc, expected_data):
    # set in IPC
    async with ipc.set(data_async_gen()) as (data_ref, getter):

        # fetch from IPC
        with getter(data_ref) as file_like_data:

            # THEN assert is the data expected
            assert file_like_data.read() == expected_data


@pytest.mark.asyncio
@pytest.mark.parametrize("in_data", [b"123456789", data_async_gen()])
async def test_none_data_ipc_handle_async_generator_and_bytes(in_data):
    ipc_obj = DaskNoneDataIPC()
    await assert_ipc_forward_equal(ipc_obj, b"123456789")


@pytest.mark.asyncio
@pytest.mark.parametrize("in_data", [b"123456789", data_async_gen()])
async def test_file_data_ipc_handle_async_generator_and_bytes(nope_logger_fixture, tmp_path, in_data):
    ipc_obj = DaskLocalFileDataIPC(base_folder=tmp_path)
    await assert_ipc_forward_equal(ipc_obj, b"123456789")


@pytest.mark.asyncio
@pytest.mark.parametrize("in_data", [b"123456789", data_async_gen()])
async def test_dask_native_ipc_handle_async_generator_and_bytes(in_data):
    async def identity(anything, **kwargs):
        return anything

    dask_client_mock = AsyncMock()
    dask_client_mock.scatter = AsyncMock(side_effect=identity)

    ipc_obj = DaskNativeDataIPC(dask_client=dask_client_mock)
    await assert_ipc_forward_equal(ipc_obj, b"123456789")

    # scatter on dask client expected to be called
    dask_client_mock.scatter.assert_called_once()
    dask_client_mock.scatter.assert_awaited()


@pytest.mark.asyncio
async def test_dask_native_ipc_basic_usage(dask_client):

    with dask_client(autoclose_asynccontext=True) as dask_client_asynccontext:
        async with dask_client_asynccontext() as client_starter:
            client = await client_starter()

            ipc_obj = DaskNativeDataIPC(dask_client=client)

            # worker function, simply read and return the data
            def worker_func(ipc_data_ref, ipc_data_get_func):
                with ipc_data_get_func(ipc_data_ref) as file_like_data:
                    return file_like_data.read()

            # set in IPC
            async with ipc_obj.set(b"123456789") as (data_ref, getter):

                # WHEN submit task to dask client
                result = await client.submit(worker_func, data_ref, getter)

                # THEN worker as fetch and read the expected data
                assert result == b"123456789"


@pytest.mark.asyncio
@pytest.mark.parametrize("in_data", [
    b"01234567890123456789012345",  # direct bytes
    data_async_gen(b"01234567890123456789012345", 5),  # async gen with chunk size smaller than write chunk size
    data_async_gen(b"01234567890123456789012345", 10),  # async gen with chunk size equal to write chunk size
    data_async_gen(b"01234567890123456789012345", 15),  # async gen with chunk size greater than write chunk size
])
async def test_file_data_ipc_write_by_chunk(nope_logger_fixture, in_data):
    max_write_at_once_size = 10
    ipc_obj = DaskLocalFileDataIPC(base_folder="", io_chunk_size=max_write_at_once_size)
    with patch("builtins.open", mock_open(read_data=b"")) as mock_file:

        # WHEN
        async with ipc_obj.set(in_data):
            # check write has been called
            write_mock = mock_file.return_value.write

            # THEN write always less or equal to the max chunk write size
            chunks_pass_in_write = [c[0][0] for c in write_mock.call_args_list]
            assert all((len(c) <= max_write_at_once_size) for c in chunks_pass_in_write)

            # THEN all content written = input data
            assert b"".join(chunks_pass_in_write) == b"01234567890123456789012345"


@pytest.mark.asyncio
async def test_file_data_ipc_track_file_count_and_size(nope_logger_fixture, tmp_path):
    ipc_obj = DaskLocalFileDataIPC(base_folder=tmp_path)

    async with ipc_obj.set(b"0123456789"):
        assert DaskLocalFileDataIPC.total_size_in_file == 10
        assert DaskLocalFileDataIPC.total_files_count == 1

        async with ipc_obj.set(b"01234"):
            assert DaskLocalFileDataIPC.total_size_in_file == 15
            assert DaskLocalFileDataIPC.total_files_count == 2

        assert DaskLocalFileDataIPC.total_size_in_file == 10
        assert DaskLocalFileDataIPC.total_files_count == 1

    assert DaskLocalFileDataIPC.total_size_in_file == 0
    assert DaskLocalFileDataIPC.total_files_count == 0


@pytest.mark.asyncio
async def test_file_data_ipc_write_clean_up_files(nope_logger_fixture):
    with patch("builtins.open", mock_open(read_data=b"")) as open_mock:
        # due to the wierdo of mock patch, using this path since patching 'os.remove' not working ...
        with patch("app.bulk_persistence.dask.dask_data_ipc.remove") as remove_mock:

            # WHEN do nothing
            async with DaskLocalFileDataIPC().set(b"42"):
                pass

            # WHEN doing regular usage
            async with DaskLocalFileDataIPC().set(b"42") as (ref, getter):
                with getter(ref) as file_data:
                    file_data.read()

            # WHEN exception occurs post write
            with suppress(ValueError):
                async with DaskLocalFileDataIPC().set(b"42"):
                    raise ValueError('fake')

            # WHEN exception occurs during write
            open_mock.return_value.write.side_effect = side_effect_raise
            with pytest.raises(ValueError):
                async with DaskLocalFileDataIPC().set(b"42"):
                    pass

            # THEN any opened files are removed
            all_opened_files = {c[0][0] for c in open_mock.call_args_list}
            all_removed_files = {c[0][0] for c in remove_mock.call_args_list}
            assert all_opened_files == all_removed_files


@pytest.mark.asyncio
async def test_data_ipc_new():
    async with DaskNoneDataIPC().set(b"42") as (ref, getter):
        with getter(ref) as file_data:
            assert file_data.read() == b"42"
