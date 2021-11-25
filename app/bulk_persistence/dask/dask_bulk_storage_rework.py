# TODO this is a temporary name

from typing import Optional, Tuple, List, Union, AsyncGenerator
import pandas as pd
from pydantic import BaseModel, Field

from app.helper.traces import with_trace
from app.utils import capture_timings, get_ctx
from app.conf import Config

# imports from bulk_persistence
from .. import MimeTypes, DataframeSerializerSync
from ..dataframe_validators import DataFrameValidationFunc, assert_df_validate, validate_index, columns_not_in_reserved_names
from ..bulk_id import new_bulk_id
from .traces import wrap_trace_process
from .errors import internal_bulk_exceptions, BulkNotProcessable, BulkSaveException
from .utils import worker_capture_timing_handlers
from .dask_data_ipc import DaskNativeDataIPC, DaskLocalFileDataIPC
from . import storage_path_builder as StoragePathBuilder
from . import session_file_meta as session_meta


def submit_with_trace(dask_client, target_func, *args, **kwargs):
    """ Submit given target_func to Distributed Dask workers and add tracing required stuff """
    kwargs['span_context'] = get_ctx().tracer.span_context
    kwargs['target_func'] = target_func
    return dask_client.submit(wrap_trace_process, *args, **kwargs)


# TODO move to dataframe deserializer ?
def deserialize(file_like_data,
                content_type: str,
                orient: Optional[str] = None) -> pd.DataFrame:
    """
    deserialized input data as pandas dataframe
    :param file_like_data: input ipc raw bytes wrapped (file-like obj)
    :param content_type: content type value (supports json and parquet)
    :param orient: in content json, orient must be provided.
    :return: pandas dataframe

    :throw: BulkNotProcessable
    """
    try:
        if MimeTypes.JSON.match(content_type):
            return DataframeSerializerSync.read_json(file_like_data, orient=orient)
        elif MimeTypes.PARQUET.match(content_type):
            return DataframeSerializerSync.read_parquet(file_like_data)
        else:
            raise ValueError("unsupported content_type")
    except Exception as e:
        raise BulkNotProcessable('parsing error') from e


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


def write_bulk_without_session(file_like_data,
                               content_type: str,
                               orient: str,
                               df_validator_func: DataFrameValidationFunc,
                               bulk_base_path: str,
                               storage_options) -> DataframeBasicDescribe:
    """
        process post data outside of a session - write data straight to blob storage
        :param file_like_data: dataframe as input ipc raw bytes wrapped (file-like obj)
        :param content_type: content type value (supports json and parquet)
        :param orient: in content json, orient must be provided.
        :param df_validator_func: option validation callable function.
        :param bulk_base_path: base path of the final object on blob storage.
        :param storage_options: storage options
        :return: basic describe of the dataframe

        :throw: BulkNotProcessable, BulkSaveException
        """
    # 1- deserialize to pandas dataframe
    df = deserialize(file_like_data, content_type, orient)

    # 2- input dataframe validation
    assert_df_validate(df, [df_validator_func, columns_not_in_reserved_names, validate_index])

    # 3- build blob filename and final full blob path
    # TODO to be reviewed: may want to create catalog here similarly to a session with a single chunk
    filename = session_meta.generate_chunk_filename(df)
    full_file_path = StoragePathBuilder.join(bulk_base_path, filename + '.parquet')

    # 4- save/upload the dataframe
    try:
        # TODO will exist
        # TODO to replace with DataframeSerializerSync.to_parquet(df, full_file_path, storage_options=storage_options)
        df.to_parquet(full_file_path, index=True, engine='pyarrow', storage_options=storage_options)
    except Exception as e:
        raise BulkSaveException('Unexpected error and save bulk') from e

    # 4- return basic describe
    return basic_describe(df)


class DaskBulkStorageFullWorkerDelegated:
    """
        Perform bulk storage and delegate all treatment in Dask workers.
    """

    # TODO to review, based on the legacy one instantiation for now
    def __init__(self, dask_bulk_storage: 'DaskBulkStorage'):
        self._parameters = dask_bulk_storage._parameters
        self._fs = dask_bulk_storage._fs
        self.client = dask_bulk_storage.client

    @property
    def protocol(self) -> str:
        return self._parameters.protocol

    @property
    def base_directory(self) -> str:
        return self._parameters.base_directory

    @property
    def storage_options(self):
        return self._parameters.storage_options

    def _get_data_ipc(self):
        """ return inter process data transfer implementation """
        if Config.dask_data_ipc.value == DaskLocalFileDataIPC.ipc_type:
            return DaskLocalFileDataIPC()
        return DaskNativeDataIPC(self.client)

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
                                        content_type: str,
                                        orient: str,
                                        df_validator_func,
                                        record_id: str,
                                        bulk_id: Optional[str] = None) -> Tuple[str, DataframeBasicDescribe]:
        """
        process post data outside of a session, delegate the entire work in Dask worker
        :throw:
            - BulkNotProcessable: in case on invalid input data
            - BulkSaveException: if store operation fails for some reasons
        """

        bulk_id = bulk_id or new_bulk_id()
        bulk_base_path = StoragePathBuilder.record_bulk_path(self.base_directory, record_id, bulk_id, self.protocol)

        # ensure directory exists for local storage, do nothing on remote storage
        self.ensure_dir_tree_exists(bulk_base_path)

        async with self._get_data_ipc().set(data) as ipc_data_descriptor:
            data = None  # unref data

            df_describe = await submit_with_trace(self.client,
                                                  write_bulk_without_session,
                                                  ipc_data_descriptor,
                                                  content_type,
                                                  orient,
                                                  df_validator_func,
                                                  bulk_base_path,
                                                  self.storage_options)

        return bulk_id, df_describe
