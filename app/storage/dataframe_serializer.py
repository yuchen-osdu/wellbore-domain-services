from io import BytesIO
from typing import Union, AnyStr, IO, Optional
from enum import Enum
from pathlib import Path
import json
import pandas as pd
import numpy as np
from app.storage.mime_types import MimeTypes
from pydantic import BaseModel
from typing import Union, List
from pandas import DataFrame as DataframeClass


class JSONOrient(Enum):
    # not allow 'table' because very verbose then comes with significant overhead
    split = 'split'
    index = 'index'
    columns = 'columns'
    records = 'records'
    values = 'values'

    @classmethod
    def get(cls, orient: Union[str, 'JSONOrient']) -> 'JSONOrient':
        return JSONOrient[orient] if isinstance(orient, str) else orient


class DataframeSerializer:
    """
        the goal is to encapsulate to (de)serialized dataframe from/to various format
        then provide unified the way to handle various topics float/double precision, compression etc...
    """
    # todo may be unified with the work from storage.blob_storage

    SupportedFormat = [MimeTypes.JSON]  # , MimeTypes.MSGPACK]
    """ these are supported format through wellbore ddms APIs """

    @classmethod
    def example_as_json(cls, orient: Union[str, JSONOrient], indent: Optional[int] = None) -> str:
        df = pd.DataFrame([[1.0, 10, 11], [1.5, 20, 21], [2.0, 30, 31]], columns=['Ref', 'col_1', 'col_2'])
        orient = JSONOrient.get(orient)
        return df.to_json(orient=orient.value, indent=indent)

    @classmethod
    def example_as_dict(cls, orient: Union[str, JSONOrient]) -> dict:
        return json.loads(cls.example_as_json(orient))

    @classmethod
    def get_schema(cls, orient: Union[str, JSONOrient]) -> dict:
        # defined here as only used to provided schema
        class SplitFormat(BaseModel):
            data: Union[List[Union[str, int, float]], List[List[Union[str, int, float]]]]
            columns: List[Union[str, int, float]] = None
            index: List[Union[str, int, float]] = None

        class IndexFormat(BaseModel):
            TODO: str

        class ColumnFormat(BaseModel):
            TODO: str

        class ValuesFormat(BaseModel):
            __root__: List[List[Union[str, int, float]]]

        class RecordsFormat(BaseModel):
            TODO: str

        schema_dict = {
            JSONOrient.split: SplitFormat.schema(),
            JSONOrient.index: IndexFormat.schema(),
            JSONOrient.columns: ColumnFormat.schema(),
            JSONOrient.values: ValuesFormat.schema(),
            JSONOrient.records: RecordsFormat.schema()
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

        return df.fillna("NaN").to_json(path_or_buf, orient=orient.value)

    @classmethod
    def read_parquet(cls, data) -> 'DataframeSerializer.DataframeClass':
        """
        :param data: bytes, path object or file-like object
        :return: dataframe
        """
        if isinstance(data, bytes):
            data = BytesIO(data)

        # will raise if contains multiple dataframe
        return pd.read_parquet(data)

    @classmethod
    def read_json(cls, data, orient: Union[str, JSONOrient]) -> 'DataframeSerializer.DataframeClass':
        """
        :param data: bytes str content (valid JSON str), path object or file-like object
        :param orient:
        :return: dataframe
        """
        orient = JSONOrient.get(orient)

        if isinstance(data, bytes):
            data = BytesIO(data)
        return pd.read_json(data, orient.value).replace("NaN", np.NaN)
