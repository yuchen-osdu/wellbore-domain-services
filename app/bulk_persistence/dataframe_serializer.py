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
from functools import partial
from io import BytesIO
from typing import Union, Optional, List, Dict

import numpy as np
import pandas as pd
from pydantic import BaseModel

from .json_orient import JSONOrient
from .mime_types import MimeTypes, MimeType
from app.pool_executor import get_pool_executor
from app.helper.traces_ot import get_tracer
_tracer = get_tracer()


class DataframeSerializerSync:
    """
    the goal is to encapsulate to (de)serialized dataframe from/to various format
    then provide unified the way to handle various topics float/double precision, compression etc...
    """

    SupportedFormat = [MimeTypes.JSON, MimeTypes.PARQUET]
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
                df: pd.DataFrame,
                orient: Union[str, JSONOrient] = JSONOrient.split,
                **kwargs) -> Optional[str]:
        """
        :param df: dataframe to dump
        :param orient: format for Json, default is split
        :param kwargs: keyword arguments will be forwarded to pandas.to_json()
        :return: None or json string of path_or_buf is None
        """
        orient = JSONOrient.get(orient)

        return df.fillna("NaN").to_json(orient=orient.value, **kwargs)

    @classmethod
    def to_parquet(cls, df: pd.DataFrame, path_or_buf=None, *, storage_options=None):
        """
        :param df: dataframe to dump
        :param path_or_buf: str or file-like object, default None, see Pandas.Dataframe.to_parquet
        :param storage_options: storage_options, default None
        :return: None or buffer
        """
        return df.to_parquet(path_or_buf, index=True, engine='pyarrow', storage_options=storage_options)

    @classmethod
    def read_parquet(cls, data, columns=None) -> pd.DataFrame:
        """
        :param data: bytes, path object or file-like object
        :param columns : list, default=None If not None, only these columns will be read from the file.
        :return: dataframe
        """
        if isinstance(data, bytes):
            data = BytesIO(data)

        # will raise if contains multiple dataframe
        return pd.read_parquet(data, columns=columns)

    @classmethod
    def read_json(cls, data, orient: Union[str, JSONOrient]) -> pd.DataFrame:
        """
        :param data: bytes str content (valid JSON str), path object or file-like object. It won't convert axes. In case
                     of orient='columns' since the indexes type is lost, it will still try to coerce index into 'int'
                     then 'float' then try convert to date time. 'Columns' will remain as string type.
                     For orient 'split' no convert at all.
        :param orient:
        :return: dataframe
        """
        if isinstance(data, bytes):
            data = BytesIO(data)

        orient = JSONOrient.get(orient)

        df = pd.read_json(
            path_or_buf=data, orient=orient.value, convert_axes=False
        ).replace("NaN", np.NaN)

        # this is a conner case, orient 'columns' implies to have all columns and index values to be passed as string
        # in JSON content.
        # In that case, their original types are lost. Since parameter 'convert_axes' is set to False, pandas won't
        # try to infer the types of the columns and index.
        # Regarding columns, it remains OK since WDMS enforces them to be string. Then, using orient 'columns' will cast
        # them to string 'by design'.
        # For the index values it's problematic. In main cases, those are integer values and it matters to have them
        # back to the original type if possible.
        #
        # Here's the tradeoff to handle the case orient='columns':
        # - no convert on columns, so remains as string type
        # - try to coerce index to 'float64' or 'int64'
        #
        # This is similar to what is done in Pandas but only for index:
        # see https://github.com/pandas-dev/pandas/blob/master/pandas/io/json/_json.py#L916
        if orient == JSONOrient.columns:
            for dtype in ['int64', 'float64']:
                try:
                    # try to coerce index type as int then float
                    df.index = df.index.astype(dtype)
                    return df
                except (TypeError, ValueError, OverflowError):
                    continue

        return df

    @classmethod
    def load(cls, file_like_data,
             content_type: MimeType,
             orient: Optional[Union[str, JSONOrient]] = None) -> pd.DataFrame:
        """
        deserialized input data as pandas dataframe
        :param file_like_data: input ipc raw bytes wrapped (file-like obj)
        :param content_type: content type value (supports json and parquet)
        :param orient: in content json, orient must be provided.
        :return: pandas dataframe

        :throw: ValueError
        """
        if content_type == MimeTypes.JSON:
            return cls.read_json(file_like_data, orient=orient)
        elif content_type == MimeTypes.PARQUET:
            return cls.read_parquet(file_like_data)
        else:
            raise ValueError(f"unsupported content_type {content_type}")


class DataframeSerializerAsync:
    def __init__(self, pool_executor=get_pool_executor()):
        self.executor = pool_executor

    @_tracer.start_as_current_span("Parquet bulk serialization")
    async def to_parquet(self, df: pd.DataFrame, *, storage_options=None) -> pd.DataFrame:
        func = partial(DataframeSerializerSync.to_parquet, df, storage_options=storage_options)
        return await asyncio.get_event_loop().run_in_executor(self.executor, func)

    @_tracer.start_as_current_span("JSON bulk serialization")
    async def to_json(self,
                      df: pd.DataFrame,
                      orient: Union[str, JSONOrient] = JSONOrient.split,
                      *args, **kwargs) -> Optional[str]:

        func = partial(DataframeSerializerSync.to_json, df, orient, *args, **kwargs)
        return await asyncio.get_event_loop().run_in_executor(self.executor, func)

    # @_tracer.start_as_current_span("Parquet bulk deserialization")
    async def read_parquet(self, data, columns=None) -> pd.DataFrame:
        return await asyncio.get_event_loop().run_in_executor(
            self.executor, DataframeSerializerSync.read_parquet, data, columns
        )

    @_tracer.start_as_current_span("Parquet JSON deserialization")
    async def read_json(self, data, orient: Union[str, JSONOrient]) -> pd.DataFrame:
        return await asyncio.get_event_loop().run_in_executor(
            self.executor, DataframeSerializerSync.read_json, data, orient
        )
