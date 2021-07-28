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

import json
import asyncio
from io import BytesIO
from typing import Union, AnyStr, IO, Optional, List, Dict

from pathlib import Path
import numpy as np
import pandas as pd
from pydantic import BaseModel
from pandas import DataFrame as DataframeClass

from .json_orient import JSONOrient
from .mime_types import MimeTypes
from app.utils import get_pool_executor
from ..helper.traces import with_trace


class DataframeSerializerSync:
    """
    the goal is to encapsulate to (de)serialized dataframe from/to various format
    then provide unified the way to handle various topics float/double precision, compression etc...
    """

    # todo may be unified with the work from storage.blob_storage

    SupportedFormat = [MimeTypes.JSON]  # , MimeTypes.MSGPACK]
    """ these are supported format through wellbore ddms APIs """

    @classmethod
    def get_schema(cls, orient: Union[str, JSONOrient]) -> dict:
        # defined here as only used to provided schema
        class SplitFormat(BaseModel):
            data: Union[List[Union[str, int, float]], List[List[Union[str, int, float]]]]
            columns: List[Union[str, int, float]] = None
            index: List[Union[str, int, float]] = None

        class ColumnFormat(BaseModel):
            __root__: Dict[str, Dict[Union[str, int, float], Union[str, int, float]]]

        schema_dict = {
            JSONOrient.split: SplitFormat.schema(),
            JSONOrient.columns: ColumnFormat.schema()
        }

        return schema_dict[JSONOrient.get(orient)]

    @classmethod
    def to_json(cls,
                df: DataframeClass,
                orient: Union[str, JSONOrient] = JSONOrient.split,
                path_or_buf: Optional[Union[str, Path, IO[AnyStr]]] = None) -> Optional[str]:
        """
        :param df: dataframe to dump
        :param orient: format for Json, default is split
        :param path_or_buf: File path or object. If not specified, the result is returned as a string.
        :return: None or json string of path_or_buf is None
        """
        orient = JSONOrient.get(orient)

        return df.fillna("NaN").to_json(path_or_buf=path_or_buf, orient=orient.value)

    @classmethod
    def read_parquet(cls, data) -> 'DataframeSerializerAsync.DataframeClass':
        """
        :param data: bytes, path object or file-like object
        :return: dataframe
        """
        if isinstance(data, bytes):
            data = BytesIO(data)

        # will raise if contains multiple dataframe
        return pd.read_parquet(data)

    @classmethod
    def read_json(cls, data, orient: Union[str, JSONOrient], convert_axes: Optional[bool] = None) -> 'DataframeSerializerAsync.DataframeClass':
        """
        :param data: bytes str content (valid JSON str), path object or file-like object
        :param orient:
        :return: dataframe
        """
        orient = JSONOrient.get(orient)

        return pd.read_json(path_or_buf=data, orient=orient.value, convert_axes=convert_axes).replace("NaN", np.NaN)


class DataframeSerializerAsync:
    def __init__(self, pool_executor=get_pool_executor()):
        self.executor = pool_executor

    @with_trace("JSON bulk serialization")
    async def to_json(self,
                      df: DataframeClass,
                      orient: Union[str, JSONOrient] = JSONOrient.split,
                      path_or_buf: Optional[Union[str, Path, IO[AnyStr]]] = None) -> Optional[str]:
        return await asyncio.get_event_loop().run_in_executor(
            self.executor, DataframeSerializerSync.to_json, df, orient, path_or_buf
        )

    @with_trace("Parquet bulk deserialization")
    async def read_parquet(self, data) -> DataframeClass:
        return await asyncio.get_event_loop().run_in_executor(
            self.executor, DataframeSerializerSync.read_parquet, data
        )

    @with_trace("Parquet JSON deserialization")
    async def read_json(self, data, orient: Union[str, JSONOrient], convert_axes: Optional[bool] = None) -> DataframeClass:
        return await asyncio.get_event_loop().run_in_executor(
            self.executor, DataframeSerializerSync.read_json, data, orient, convert_axes
        )
