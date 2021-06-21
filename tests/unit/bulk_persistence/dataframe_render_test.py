import pytest
from io import BytesIO

from fastapi import HTTPException

from app.model.model_chunking import GetDataParams
from app.routers.ddms_v3.bulk_v3 import DataFrameRender, get_df_from_request
import pandas as pd
from pandas.testing import assert_frame_equal


@pytest.mark.parametrize("requested, df_columns, expected", [
    (["X"],           {"X"},                   ["X"]),
    ([],              {"X"},                   []),
    (["X", "Y", "Z"], {"X", "Y"},              ["X", "Y"]),
    (["X", "Y", "Z"], {"X", "Y", "Z"},         ["X", "Y", "Z"]),
    (["2D"],          {"X", "2D[0]", "2D[1]"}, ["2D[0]", "2D[1]"]),
    (["2D[0]"],       {"X", "2D[0]", "2D[1]"}, ["2D[0]"]),
    (["X", "2D"],     {"X", "2D[0]", "2D[1]"}, ["X", "2D[0]", "2D[1]"]),
])
def test_get_matching_column(requested, df_columns, expected):
    result = DataFrameRender.get_matching_column(requested, df_columns)
    assert set(result) == set(expected)


def assert_df_in_parquet(expected_df, content):
    # let read it
    content = BytesIO(content)
    content.seek(0)
    actual_df = pd.read_parquet(content, "pyarrow")
    assert_frame_equal(expected_df, actual_df)


@pytest.fixture
def default_get_params():
    return GetDataParams(describe=False, limit=None, curves=None, offset=None)


@pytest.fixture
def basic_dataframe():
    return pd.DataFrame([[10, 11], [20, 21], [30, 31]], index=[1, 2, 3], columns=['c1', 'c2'])


@pytest.mark.asyncio
@pytest.mark.parametrize("accept", [
    None,  # default is parquet
    "",  # default is parquet
    "application/x-parquet",
    "application/parquet",
    "application/json, application/x-parquet"  # is case of multiple, prioritize parquet
])
async def test_df_render_accept_parquet(default_get_params, basic_dataframe, accept):
    response = await DataFrameRender.df_render(basic_dataframe, default_get_params, accept)

    assert 'application/x-parquet' == response.headers.get('Content-Type')
    assert_df_in_parquet(basic_dataframe, response.body)


@pytest.mark.asyncio
async def test_df_render_accept_json(default_get_params, basic_dataframe):
    response = await DataFrameRender.df_render(basic_dataframe, default_get_params, "application/json")
    assert 'application/json' == response.headers.get('Content-Type')
    actual = pd.read_json(response.body, orient='columns')
    assert_frame_equal(basic_dataframe, actual)


class RequestMock:
    def __init__(self, headers: dict = {}, body=None):
        self.headers = headers
        self.body_content = body

    async def body(self):
        return self.body_content


@pytest.mark.asyncio
async def test_get_df_from_request_parquet(basic_dataframe):
    request = RequestMock({"Content-Type": "application/x-parquet"},
                          basic_dataframe.to_parquet(engine='pyarrow', index=True))

    actual_df = await get_df_from_request(request)
    assert_frame_equal(basic_dataframe, actual_df)


@pytest.mark.asyncio
async def test_get_df_from_request_json(basic_dataframe):
    request = RequestMock({"Content-Type": "application/json"},
                          basic_dataframe.to_json(orient='split'))

    actual_df = await get_df_from_request(request, orient='split')
    assert_frame_equal(basic_dataframe, actual_df)


@pytest.mark.asyncio
@pytest.mark.parametrize("content_type, status", [
    ("application/json", 422),
    ("application/x-parquet", 422),
    ("image/jpeg", 400)
])
async def test_get_df_from_request_invalid_raise(content_type, status):
    request = RequestMock({"Content-Type": content_type}, b'some invalid data')
    with pytest.raises(HTTPException) as ex_info:
        await get_df_from_request(request, orient='split')
    exception = ex_info.value
    assert exception.status_code == status
