# TODO this is a temporary name

from typing import Optional, Tuple, List, Union, AsyncGenerator
import json

import fsspec
import pandas as pd
from pydantic import BaseModel, Field

from app.helper.traces import with_trace
from app.utils import capture_timings
from app.conf import Config

# imports from bulk_persistence
from ..json_orient import JSONOrient
from ..mime_types import MimeType
from ..dataframe_serializer import DataframeSerializerSync
from ..dataframe_validators import (DataFrameValidationFunc, assert_df_validate, validate_index,
                                    columns_not_in_reserved_names)
from ..bulk_id import new_bulk_id
from .errors import internal_bulk_exceptions, BulkNotProcessable, BulkSaveException
from .utils import worker_capture_timing_handlers
from .traces import trace_dataframe_attributes, submit_with_trace
from .dask_data_ipc import DaskNativeDataIPC, DaskLocalFileDataIPC
from . import storage_path_builder as StoragePathBuilder
from . import session_file_meta as session_meta


# TODO move to a more appropriate file?
class DataframeBasicDescribe(BaseModel):
    row_count: int = Field(alias="rowCount")
    column_count: int = Field(alias="columnCount")
    columns: List[str] = Field(alias="columns")
    index_start: int = Field(alias="indexStart")
    index_end: int = Field(alias="indexEnd")


def basic_describe(df: pd.DataFrame) -> DataframeBasicDescribe:
    full_cols = df.columns.tolist()
    if len(full_cols) > 20:  # truncate if too many columns, show 10 first and 10 last
        cols = [*full_cols[0:10], '...', *full_cols[-10:]]
    else:
        cols = full_cols

    return DataframeBasicDescribe(rowCount=len(df.index),
                                  columnCount=len(full_cols),
                                  columns=cols,
                                  indexStart=int(df.index[0]),
                                  indexEnd=int(df.index[-1]))


def read_dataframe(file_like_data,
                   content_type: MimeType,
                   orient: Optional[Union[str, JSONOrient]] = None) -> pd.DataFrame:
    try:
        return DataframeSerializerSync.load(file_like_data, content_type, orient)
    except Exception as e:
        raise BulkNotProcessable(f'parsing error: {e}') from e


def write_bulk_without_session(data_handle,
                               data_getter,
                               content_type: MimeType,
                               df_validator_func: DataFrameValidationFunc,
                               bulk_base_path: str,
                               storage_options) -> DataframeBasicDescribe:
    """
        process post data outside of a session - write data straight to blob storage
        :param data_handle: dataframe as input ipc raw bytes wrapped (file-like obj)
        :param data_getter: function to get data from the handle
        :param content_type: content type value as mime type (supports json and parquet)
        :param df_validator_func: option validation callable function.
        :param bulk_base_path: base path of the final object on blob storage.
        :param storage_options: storage options
        :return: basic describe of the dataframe

        :throw: BulkNotProcessable, BulkSaveException
        """
    # 1- deserialize to pandas dataframe
    with data_getter(data_handle) as file_like_data:
        df = read_dataframe(file_like_data, content_type, JSONOrient.split)
    data_handle = None  # unref

    # 2- input dataframe validation
    assert_df_validate(df, [df_validator_func, columns_not_in_reserved_names, validate_index])
    # TODO this requires a context, not available in worker, use info from basic describe after return?
    # trace_dataframe_attributes(df)

    # 3- build blob filename and final full blob path
    # TODO to be reviewed: may want to create catalog here similarly to a session with a single chunk
    filename = session_meta.generate_chunk_filename(df)
    full_file_path = StoragePathBuilder.join(bulk_base_path, filename + '.parquet')

    # 4- save/upload the dataframe
    try:
        DataframeSerializerSync.to_parquet(df, full_file_path, storage_options=storage_options)
    except Exception as e:
        raise BulkSaveException('Unexpected error and save bulk') from e

    # 4- return basic describe
    return basic_describe(df)


def add_chunk_in_session(data_handle,
                         data_getter,
                         content_type: MimeType,
                         df_validator_func: DataFrameValidationFunc,
                         record_session_path: str,
                         storage_options) -> DataframeBasicDescribe:
    """
        process add chunk data inside of a session
        :param data_handle: input ipc raw bytes wrapped (file-like obj)
        :param data_getter: function to get data from the handle
        :param content_type: content type as mime type (supports json and parquet)
        :param df_validator_func: option validation callable function.
        :param record_session_path: base path to the session associated to the record.
        :param storage_options: storage options
        :return: basic describe of the dataframe

        :throw: BulkNotProcessable, BulkSaveException

        """
    # 1- deserialize
    with data_getter(data_handle) as file_like_data:
        df = read_dataframe(file_like_data, content_type, JSONOrient.split)
    data_handle = None  # unref

    # 2- perf some check
    assert_df_validate(df, [df_validator_func, columns_not_in_reserved_names, validate_index])
    # TODO this requires a context, not available in worker, use info from basic describe after return?
    # trace_dataframe_attributes(df)

    # sort column by names # TODO could it be avoided ? then we could keep input untouched and save serialization step?
    df = df[sorted(df.columns)]

    # 3- build blob filename and final full blob path
    filename = session_meta.generate_chunk_filename(df)

    # 4- build and push chunk meta file
    meta_file_path, protocol = StoragePathBuilder.remove_protocol(f'{record_session_path}/{filename}.meta')
    # TODO ctor each time (so trigger a do_connect each time), avoidable?
    fs = fsspec.filesystem(protocol, **(storage_options if storage_options else {}))
    with fs.open(meta_file_path, 'w') as outfile:
        json.dump(session_meta.build_chunk_metadata(df), outfile)

    # 5- save/upload the dataframe
    parquet_file_path = f'{record_session_path}/{filename}.parquet'
    try:
        DataframeSerializerSync.to_parquet(df, parquet_file_path, storage_options=storage_options)
    except Exception as e:
        raise BulkSaveException('Unexpected error and save bulk') from e

    # 6- return basic describe
    return basic_describe(df)


# TODO
TEMP_FORCE_IPC_WITH_FILE = True

class DaskBulkStorageFullWorkerDelegated:
    """
        Perform bulk storage and delegate all treatment in Dask workers.
    """

    # TODO to review, based on the legacy one instantiation for now
    def __init__(self, dask_bulk_storage: 'DaskBulkStorage'):
        self._parameters = dask_bulk_storage._parameters
        self._fs = dask_bulk_storage._fs
        self.client = dask_bulk_storage.client
        if TEMP_FORCE_IPC_WITH_FILE or Config.dask_data_ipc.value == DaskLocalFileDataIPC.ipc_type:
            self._data_ipc = DaskLocalFileDataIPC()
        else:
            self._data_ipc = DaskNativeDataIPC(self.client)

    @property
    def protocol(self) -> str:
        return self._parameters.protocol

    @property
    def base_directory(self) -> str:
        return self._parameters.base_directory

    @property
    def storage_options(self):
        return self._parameters.storage_options

    def ensure_dir_tree_exists(self, path: str):
        path_wo_protocol, protocol = StoragePathBuilder.remove_protocol(path)

        # on local storage only """
        if protocol == 'file':
            self._fs.mkdirs(path_wo_protocol, exist_ok=True)

    @internal_bulk_exceptions
    @capture_timings('post_data_without_session', handlers=worker_capture_timing_handlers)
    @with_trace('post_data_without_session')
    async def post_data_without_session(self,
                                        data: Union[bytes, AsyncGenerator[bytes, None]],
                                        content_type: MimeType,
                                        df_validator_func: DataFrameValidationFunc,
                                        record_id: str,
                                        bulk_id: Optional[str] = None) -> Tuple[str, DataframeBasicDescribe]:
        """
        process post data outside of a session, delegate the entire work in Dask worker. It constructs the path
        for the bulk in current context, prepare and
        :throw:
            - BulkNotProcessable: in case on invalid input data
            - BulkSaveException: if store operation fails for some reasons
        """

        bulk_id = bulk_id or new_bulk_id()
        bulk_base_path = StoragePathBuilder.record_bulk_path(self.base_directory, record_id, bulk_id, self.protocol)

        # ensure directory exists for local storage, do nothing on remote storage
        self.ensure_dir_tree_exists(bulk_base_path)

        async with self._data_ipc.set(data) as (data_handle, data_getter):
            data = None  # unref data

            df_describe = await submit_with_trace(self.client,
                                                  write_bulk_without_session,
                                                  data_handle,
                                                  data_getter,
                                                  content_type,
                                                  df_validator_func,
                                                  bulk_base_path,
                                                  self.storage_options)

        return bulk_id, df_describe

    @internal_bulk_exceptions
    @capture_timings('add_chunk_in_session', handlers=worker_capture_timing_handlers)
    @with_trace('add_chunk_in_session')
    async def add_chunk_in_session(self,
                                   data: Union[bytes, AsyncGenerator[bytes, None]],
                                   content_type: MimeType,
                                   df_validator_func: DataFrameValidationFunc,
                                   record_id: str,
                                   session_id: str,
                                   bulk_id: Optional[str] = None) -> Tuple[str, DataframeBasicDescribe]:
        """
        add a chunk data inside a session, delegate the entire work in Dask worker
        :throw:
            - BulkNotProcessable: in case on invalid input data
            - BulkSaveException: if store operation fails for some reasons
        """

        bulk_id = bulk_id or new_bulk_id()
        base_path = StoragePathBuilder.record_session_path(self.base_directory, session_id, record_id, self.protocol)

        # ensure directory exists for local storage, do nothing on remote storage
        self.ensure_dir_tree_exists(base_path)

        async with self._data_ipc.set(data) as (data_handle, data_getter):
            data = None  # unref data

            df_describe = await submit_with_trace(self.client,
                                                  add_chunk_in_session,
                                                  data_handle,
                                                  data_getter,
                                                  content_type,
                                                  df_validator_func,
                                                  base_path,
                                                  self.storage_options)

        return bulk_id, df_describe
