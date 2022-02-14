from typing import List
import json

import fsspec
import pandas as pd

from app.bulk_persistence.dask.utils import WDMS_INDEX_NAME
from app.model.model_chunking import DataframeBasicDescribe

# imports from bulk_persistence
from ..json_orient import JSONOrient
from ..mime_types import MimeType
from ..dataframe_serializer import DataframeSerializerSync
from ..dataframe_validators import (DataFrameValidationFunc, assert_df_validate, validate_index,
                                    columns_not_in_reserved_names, validate_number_of_columns)

from .errors import BulkNotProcessable, BulkSaveException
from . import storage_path_builder as path_builder
from . import session_file_meta as session_meta

from ..consistency_checks import DataConsistencyChecks

"""
Contains functions related to writing bulk that mean to be run inside worker
"""


def basic_describe(df: pd.DataFrame) -> DataframeBasicDescribe:
    full_cols = df.columns.tolist()
    if len(full_cols) > 20:  # truncate if too many columns, show 10 first and 10 last
        cols = [*full_cols[0:10], '...', *full_cols[-10:]]
    else:
        cols = full_cols

    index_exists = len(df.index)
    return DataframeBasicDescribe(rowCount=len(df.index),
                                  columnCount=len(full_cols),
                                  columns=cols,
                                  indexStart=str(df.index[0]) if index_exists else "0",
                                  indexEnd=str(df.index[-1]) if index_exists else "0",
                                  indexType=str(df.index.dtype) if index_exists else "")


def write_bulk_without_session(data_handle,
                               data_getter,
                               content_type: MimeType,
                               df_validator_func: DataFrameValidationFunc,
                               bulk_base_path: str,
                               storage_options,
                               consistency_checks: DataConsistencyChecks,
                               record: "Record",
                               ) -> DataframeBasicDescribe:
    """
        process post data outside of a session - write data straight to blob storage

        :param data_handle: dataframe as input ipc raw bytes wrapped (file-like obj)
        :param data_getter: function to get data from the handle
        :param content_type: content type value as mime type (supports json and parquet)
        :param df_validator_func: option validation callable function.
        :param bulk_base_path: base path of the final object on blob storage.
        :param storage_options: storage options
        :param consistency_checks: option consistency checks object
        :param record:  the entity to which the bulk belongs
        :return: basic describe of the dataframe

        :throw: BulkNotProcessable, BulkSaveException
        """
    # 1- deserialize to pandas dataframe
    try:
        with data_getter(data_handle) as file_like_data:
            df = DataframeSerializerSync.load(file_like_data, content_type, JSONOrient.split)
    except Exception as e:
        raise BulkNotProcessable(f'parsing error: {e}') from e
    data_handle = None  # unref

    # 2- input dataframe validation
    assert_df_validate(df, [df_validator_func, validate_number_of_columns, columns_not_in_reserved_names, validate_index])

    # 2(bis)- checks data consistency
    consistency_checks.check_bulk_consistency_on_post_bulk(record, df)

    # set the name of the index column
    df.index.name = WDMS_INDEX_NAME

    # 3- build blob filename and final full blob path
    filename = session_meta.generate_chunk_filename(df)
    full_file_path = path_builder.join(bulk_base_path, filename + '.parquet')

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
    try:
        with data_getter(data_handle) as file_like_data:
            df = DataframeSerializerSync.load(file_like_data, content_type, JSONOrient.split)
    except Exception as e:
        raise BulkNotProcessable(f'parsing error: {e}') from e
    data_handle = None  # unref

    # 2- perf some check
    assert_df_validate(df, [df_validator_func, validate_number_of_columns, columns_not_in_reserved_names, validate_index])

    # sort column by names and set index column name  # TODO could it be avoided ? then we could keep input untouched and save serialization step?
    df = df[sorted(df.columns)]
    df.index.name = WDMS_INDEX_NAME

    # 3- build blob filename and final full blob path
    filename = session_meta.generate_chunk_filename(df)

    # 4- build and push chunk meta file
    meta_file_path, protocol = path_builder.remove_protocol(f'{record_session_path}/{filename}.meta')

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
