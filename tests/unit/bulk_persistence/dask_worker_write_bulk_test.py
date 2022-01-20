import json
from io import BytesIO, StringIO
from unittest.mock import patch
from glob import glob

import pytest
import pandas as pd
from pandas.testing import assert_frame_equal

from app.bulk_persistence import MimeTypes
from app.bulk_persistence.dask.utils import WDMS_INDEX_NAME

from app.bulk_persistence.dask.dask_worker_write_bulk import (basic_describe,
                                                              DataframeBasicDescribe,
                                                              write_bulk_without_session,
                                                              add_chunk_in_session)
from app.bulk_persistence.dask.errors import BulkNotProcessable, BulkSaveException
from app.bulk_persistence.dataframe_validators import no_validation




def dataframe_to_format(df, data_format: str, as_stream=False):
    if 'parquet' in data_format:
        data = df.to_parquet(engine="pyarrow")
        return BytesIO(data) if as_stream else data
    elif 'json' in data_format:
        data = df.to_json(orient='split', date_format='iso')
        return StringIO(data) if as_stream else data
    else:
        raise ValueError(f"Unknown content-type: '{data_format}'")


def test_basic_describe():
    df = pd.DataFrame({'A': [1, 2, 3], 'B': [4, 5, 6]})

    assert basic_describe(df) == DataframeBasicDescribe(
        rowCount=3,
        columnCount=2,
        columns=['A', 'B'],
        indexStart='0',
        indexEnd='2',
        indexType='int64'
    )


def test_basic_describe_truncates_columns():
    df = pd.DataFrame({str(i): [i] for i in range(100)})

    result = basic_describe(df)
    assert result.column_count == 100
    assert len(result.columns) == 21


# so far post_data and add_chunk takes same input, validate similarly and throw same exceptions
@pytest.mark.parametrize("method_to_test", [write_bulk_without_session, add_chunk_in_session])
def test_post_bulk_not_processable_cases(method_to_test, tmp_path):
    def as_bytes_io(content):
        return BytesIO(content)

    # unsupported content type
    with pytest.raises(BulkNotProcessable):
        method_to_test(b'123', as_bytes_io, 'invalid_content_type', no_validation, '', None)

    # empty input as json format
    with pytest.raises(BulkNotProcessable):
        method_to_test(b'', as_bytes_io, MimeTypes.JSON, no_validation, '', None)

    # empty input as parquet format
    with pytest.raises(BulkNotProcessable):
        method_to_test(b'', as_bytes_io, MimeTypes.PARQUET, no_validation, '', None)

    # custom validation failure
    with pytest.raises(BulkNotProcessable):
        data = pd.DataFrame({'1': [10], '2': [20]}).to_parquet(engine='pyarrow')
        method_to_test(data, as_bytes_io, MimeTypes.PARQUET,
                                      lambda _: (False, "some error"), '', None)

    # index not numerical
    with pytest.raises(BulkNotProcessable):
        df = pd.DataFrame({'1': ['A'], '2': ['B']})
        df.set_index('1')
        data = pd.DataFrame(df).to_parquet(engine='pyarrow')
        method_to_test(data, as_bytes_io, MimeTypes.PARQUET,
                                      lambda _: (False, "some error"), '', None)

    # index not unique
    with pytest.raises(BulkNotProcessable):
        df = pd.DataFrame({'A': [1, 1], 'B': [2, 2]})
        df.set_index('A')
        data = df.to_parquet(engine='pyarrow')
        method_to_test(data, as_bytes_io, MimeTypes.PARQUET,
                                      lambda _: (False, "some error"), '', None)

    # save error
    data = pd.DataFrame({'A': [1], 'B': [4]}).to_parquet(engine='pyarrow', index=True)
    with patch.object(pd.DataFrame, 'to_parquet', side_effect=lambda *args, **kwargs: 0/0):
        with pytest.raises(BulkSaveException):
            method_to_test(data, as_bytes_io, MimeTypes.PARQUET, no_validation, tmp_path, None)


@pytest.mark.parametrize("content_type", [
    MimeTypes.PARQUET,
    MimeTypes.JSON
])
def test_write_bulk_without_session_success(content_type):
    df = pd.DataFrame({'A': [1, 2, 3], 'B': [4, 5, 6]})
    data = dataframe_to_format(df, content_type.type, True)
    with patch.object(pd.DataFrame, 'to_parquet') as mock_method:
        result = write_bulk_without_session(data, lambda x: x, content_type, no_validation,
                                               'my_path', {'storage_opt1': 42})
        mock_method.assert_called_once()

        args, kwargs = mock_method.call_args_list[0]
        assert args[0].startswith('my_path')
        assert kwargs['storage_options'] == {'storage_opt1': 42}

        assert result == basic_describe(df)


@pytest.mark.parametrize("content_type", [
    MimeTypes.PARQUET,
    MimeTypes.JSON
])
def test_write_chunk_in_session_success(content_type, tmp_path):
    # GIVEN
    df = pd.DataFrame({'A': [1, 2, 3], 'B': [4, 5, 6]})
    data = dataframe_to_format(df, content_type.type, True)

    # WHEN
    result = add_chunk_in_session(data, lambda x: x, content_type, no_validation, tmp_path, None)

    # THEN output basic describe matches
    assert result == DataframeBasicDescribe(
        rowCount=3,
        columnCount=2,
        columns=['A', 'B'],
        indexStart='0',
        indexEnd='2',
        indexType='int64'
    )

    # and THEN meta file produced as a valid json
    meta_files = [f for f in tmp_path.glob('*.meta')]
    assert len(meta_files) == 1
    with open(meta_files[0]) as f:
        json.load(f)

    # and THEN dataframe saved as parquet format
    parquet_files = [f for f in tmp_path.glob('*.parquet')]
    assert len(parquet_files) == 1
    loaded_df = pd.read_parquet(parquet_files[0])
    df.index.name = WDMS_INDEX_NAME
    assert_frame_equal(df, loaded_df)
