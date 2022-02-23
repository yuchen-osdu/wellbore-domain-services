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

import asyncio
import uuid
from asyncio import iscoroutinefunction

from contextlib import asynccontextmanager

from io import BytesIO
from os import path, remove
from typing import (
    Any,
    Callable,
    Coroutine,
    Dict,
    NamedTuple,
    Optional,
    Tuple,
    Union,
)

import pandas as pd
import pyarrow as pa
import pyarrow.feather as feather
import pyarrow.parquet as pq

from app.utils import get_pool_executor, get_wdms_temp_dir
from .dataframe_serializer import DataframeSerializerAsync

from .blob_bulk import BlobBulk
from .mime_types import MimeType, MimeTypes

# Here are functions to (de)serializing) bulk data only, no knowledge at all regarding the domain models, only raw data
# here
# TODO NAMING IS CURRENTLY BAD
# TODO data munging (mainly deals with missing values - df.fillna(a value representing Nan))
# TODO will do some optimization after, may be use hd5 to speed up the write dans secondly run a background task to
# to write a parquet format, here are some potential strategy:
# - using faster format, e.g. hd5
# - threshold about the busyness of the service (if not busy and not huge data -> direct write)
# - better proc fork and arg serialization
from ..helper.traces import with_trace


def export_to_parquet(
    path_like: str, dataframe: pd.DataFrame
) -> Tuple[str, Dict[str, str]]:
    # parquet v2 has less restrictions concerning format (for example number as column name)
    pq.write_table(
        pa.Table.from_pandas(dataframe, preserve_index=True),
        path_like,
        version="2.6",
        compression="snappy",
    )
    return path_like, {"content_type": MimeTypes.PARQUET.type}


def load_from_parquet(data) -> pd.DataFrame:
    """ data = bytes, str, pyarrow.NativeFile, or file-like object """
    if isinstance(data, bytes):
        data = pa.BufferReader(data)
    return pq.read_table(data).to_pandas()


def export_to_feather(
    filename: str, dataframe: pd.DataFrame
) -> Tuple[str, Dict[str, str]]:
    feather.write_feather(
        pa.Table.from_pandas(dataframe, preserve_index=True),
        filename,
        compression="lz4",
    )
    return filename, {"content_type": MimeTypes.FEATHER.type}


def load_from_feather(data) -> pd.DataFrame:
    """ data = bytes, str, pyarrow.NativeFile, or file-like object """
    if isinstance(data, bytes):
        data = feather.BufferReader(data)
    return feather.read_table(data).to_pandas()


class BlobFileExporter(NamedTuple):
    mime_type: MimeType
    writer_fn: Union[
        Callable[[str, pd.DataFrame], Any], Coroutine[str, pd.DataFrame, Any]
    ]

    def match(self, str_value: str) -> bool:
        return self.mime_type.match(str_value)


class BlobFileExporters:
    PARQUET = BlobFileExporter(MimeTypes.PARQUET, export_to_parquet)
    FEATHER = BlobFileExporter(MimeTypes.FEATHER, export_to_feather)

    @classmethod
    def from_string(cls, value: str) -> BlobFileExporter:
        if BlobFileExporters.PARQUET.match(value):
            return BlobFileExporters.PARQUET
        if BlobFileExporters.FEATHER.match(value):
            return BlobFileExporters.FEATHER
        raise KeyError("unknown file type " + value)


class BlobFileImporter(NamedTuple):
    mime_type: MimeType
    reader_fn: Union[
        Callable[[str, pd.DataFrame], Any], Coroutine[str, pd.DataFrame, Any]
    ]

    def match(self, str_value: str) -> bool:
        return self.mime_type.match(str_value)


class BlobFileImporters:
    PARQUET = BlobFileImporter(MimeTypes.PARQUET, load_from_parquet)
    FEATHER = BlobFileImporter(MimeTypes.FEATHER, load_from_feather)

    @classmethod
    def from_string(cls, value: str) -> BlobFileImporter:
        if cls.PARQUET.match(value):
            return cls.PARQUET
        if cls.FEATHER.match(value):
            return cls.FEATHER
        raise KeyError('unknown file type ' + value)


def _expand_args(args: Tuple[Callable[[str, pd.DataFrame], Tuple[str, str]], str, pd.DataFrame]):
    writer_fn, filename, df = args
    return writer_fn(filename, df)


async def _run_export_to_file_in_executor(filename: str,
                                          dataframe: pd.DataFrame,
                                          executor,
                                          exporter_fn: Callable[[str, pd.DataFrame], Tuple[str, str]]):
    return await asyncio.get_event_loop().run_in_executor(executor,
                                                          _expand_args,
                                                          (exporter_fn, filename, dataframe))


def get_default_exporter_executor():
    return get_pool_executor()


@asynccontextmanager
async def create_and_write_blob(
        table: pd.DataFrame, *,
        file_exporter: BlobFileExporter = BlobFileExporters.PARQUET,
        out_dir=None,
        blob_id: Optional[str] = None,
        executor=get_default_exporter_executor(),
        custom_export_to_file_fn=None):
    assert file_exporter or custom_export_to_file_fn
    """
    This function take inputs data, creates a pandas dataframe and dumps it into a file in a given. Supported output
    format are listed in BlobFileTypes which point to a dedicated writer/exporter function. It possible to provide a
    custom writer/exported function, it mainly for testing purposes. It also possible to control if the write/export
    operation must be run in an executor or not. This option is for testing as well but almost to update in future what
    is the best way to handle it because it appears to be a blocking operation which is potentially problematic in a 
    heavily async context.
    :param index_data: indexes values
    :param values: actual values
    :param row_wise: True if row wise, False if column wise
    :param columns_array: columns (head) values
    :param out_type: data format to write
    :param out_dir: path_like, if none will use temporary folder.
    :param blob_id: if none, will be generated.
    :param executor: executor to use, if set to None, no executor will be used. If executor is not None, then the writer
        must NOT be an async/coroutine function
    :param custom_export_to_file_fn: custom writer, either a coroutine or a sync fn, in that case out_type will be
        ignored out_filename, if provided will be passed as it to the write_coroutine as bulk id, it must provide a
        tuple(file: Union[str, bytes], metadata: dict[str, str])
        if file is str, it means file path
    :return: BlobBulk
    
    Expected to be used as within a context as such:
    
    > async with create_and_write_blob(...) as blob:
    >   # blob.data as a IO.base, mainly same as file 
    >
    
    """
    assert isinstance(table, pd.DataFrame), f"Unsupported type for table: {type(table)}, must be dataframe"
    df = table

    # Build the output filename which will be used as bulk id
    blob_id = blob_id or str(uuid.uuid4())
    out_filename = blob_id + file_exporter.mime_type.extension
    out_path = path.join(out_dir or get_wdms_temp_dir(), out_filename)

    # Dump/Export the dataframe into a file format
    export_to_file_function = custom_export_to_file_fn or file_exporter.writer_fn

    if executor is None:
        if iscoroutinefunction(export_to_file_function):
            file_meta_pair = await export_to_file_function(out_path, df)
        else:
            assert callable(export_to_file_function)
            file_meta_pair = export_to_file_function(out_path, df)
    else:
        assert not iscoroutinefunction(export_to_file_function), 'cannot use a coroutine with executor'
        file_meta_pair = await _run_export_to_file_in_executor(out_path, df, executor, export_to_file_function)

    metadata = file_meta_pair[1] or {}
    source = file_meta_pair[0]
    content_type = next((v for k, v in metadata.items() if k.replace('-', '').lower() == 'contenttype'), None)

    if isinstance(source, str):
        with open(source, 'rb') as file:
            yield BlobBulk(id=blob_id, data=file, content_type=content_type, metadata=metadata)
        # clean up
        remove(source)
    elif isinstance(source, bytes):
        yield BlobBulk(id=blob_id, data=BytesIO(source), content_type=content_type, metadata=metadata)
    else:
        raise RuntimeError(f'unexpected type {source} returned by bulk exporter function')


@with_trace('read_blob')
async def read_blob(blob: BlobBulk):
    return await DataframeSerializerAsync().read_parquet(blob.data)
