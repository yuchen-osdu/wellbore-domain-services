import pytest
from io import BytesIO
import pandas as pd
from pandas.testing import assert_frame_equal

from fastapi import HTTPException

from app.bulk_persistence import JSONOrient, MimeTypes
from app.bulk_persistence.dask.errors import BulkCurvesNotFound
from app.model.model_chunking import GetDataParams
from app.routers.bulk.bulk_routes import DataFrameRender
from app.routers.bulk.utils import get_df_from_request
from tests.unit.generate_data import generate_df
from tests.unit.test_utils import nope_logger_fixture


@pytest.mark.parametrize("requested, df_columns, expected", [
    (["X"],           {"X"},                        ["X"]),
    ([],              {"X"},                        []), # empty request
    (["X", "Y", "Z"], {"X", "Y", "Z"},              ["X", "Y", "Z"]),
    (["Y", "X"],      {"X", "Y", "Z"},              ["Y", "X"]),
    (["2D"],          {"X", "2D[0]", "2D[1]"},      ["2D[0]", "2D[1]"]),
    (["2D"],          {"2D[2]", "2D[10]"},          ["2D[2]", "2D[10]"]), # natural sort
    (["2D[0:1]"],     {"X", "2D[0]", "2D[1]"},      ["2D[0]", "2D[1]"]),
    (["2D[1:3]"],     {"X", "2D[0]", "2D[1]"},      ["2D[1]"]),
    (["2D[1:3]"],     {"2D[0]", "2D[1]", "2D[3]"},  ["2D[1]", "2D[3]"]),
    (["2D[0]"],       {"X", "2D[0]", "2D[1]"},      ["2D[0]"]),
    (["X", "2D"],     {"X", "2D[0]", "2D[1]"},      ["X", "2D[0]", "2D[1]"]),
    (["2D"],          {"2D[str]", "2D[0]"},         ["2D[0]", "2D[str]"]),
    ([""],            {""},                         [""]),  # empty string
    (["X", "X", "X"], {"X", "Y"},                   ["X"]), # removes duplication
    (["NMR[0:2]"],    {"NMR[0]", "NMR[1]", "GR[2]"},  ["NMR[0]", "NMR[1]"]),  # ranges
    (["NMR[0:2]", "GR[2:4]"],       {"NMR[0]", "NMR[1]", "GR[2]"},  ["NMR[0]", "NMR[1]", "GR[2]"]),  # multiple ranges
    (["X[0]", "X[0:5]", "X[0:1]"],  {"X[0]", "X[1]", "X[2]"},       ["X[0]", "X[1]", "X[2]"]),  # removes duplication in overlapping ranges
    (["X[0]"],        {"X[0]", "X[0][1]"},          ["X[0]", "X[0][1]"]),  # ensure that we capture only the last [..]
    (["X[0]"],        {"X[0][0]", "X[0][1]"},       ["X[0][0]", "X[0][1]"]), 
    (["X[0][0:1]"],      {"X[0][0]", "X[0][1]"},       ["X[0][0]", "X[0][1]"]), 
    (["X[0][1:1]"],      {"X[0][0]", "X[0][1]"},       ["X[0][1]"]), 
])
def test_get_matching_column_success(requested, df_columns, expected):
    result = DataFrameRender.get_matching_columns(requested, set(df_columns))
    # check order
    assert result == expected


@pytest.mark.parametrize("requested, df_columns, detail", [
    (["X", "Y", "Z"], {"X", "Y"},                   ["Z"]),
    (["2D[str:0]"],   {"2D[str]", "2D[0]"},         ["2D[str:0]"]),
    ([""],            {},                           [""]),  # empty string
    (["a"],           {"A"},                        ["a"]),  # case sensitive
    (["Y[4:]"], {"Y[4], Y[5], Y[6]"}, ["Y[4:]"]),   # incomplete range?
    (["Y[:4]"], {"Y[4], Y[5], Y[6]"}, ["Y[:4]"]),   # incomplete range?
    (["2D[5]"], {"X", "2D[0]", "2D[1]"}, ["2D[5]"]),
])
def test_get_matching_column_404(requested, df_columns, detail):
    with pytest.raises(BulkCurvesNotFound) as execinfo:
        result = DataFrameRender.get_matching_columns(requested, set(df_columns))
    assert execinfo.value.args[0] == f'bulk for curves: {detail} not found'


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
async def test_df_render_empty_accept_raise(default_get_params, basic_dataframe, nope_logger_fixture):
    with pytest.raises(ValueError):
        await DataFrameRender.df_render(basic_dataframe, default_get_params, render_type=None)


@pytest.mark.asyncio
async def test_df_render_accept_parquet(default_get_params, basic_dataframe):
    response = await DataFrameRender.df_render(basic_dataframe, default_get_params, MimeTypes.PARQUET)

    assert response.headers.get('Content-Type') == "application/x-parquet"
    assert_df_in_parquet(basic_dataframe, response.body)


@pytest.mark.asyncio
@pytest.mark.parametrize("orient", [JSONOrient.split, JSONOrient.columns])
async def test_df_render_accept_json(default_get_params, basic_dataframe, orient):
    response = await DataFrameRender.df_render(basic_dataframe, default_get_params, MimeTypes.JSON, orient)
    assert response.headers.get('Content-Type') == "application/json"
    actual = pd.read_json(response.body, orient=orient)
    assert_frame_equal(basic_dataframe, actual)


@pytest.mark.asyncio
async def test_df_render_describe():
    columns = [f'var_{i}' for i in range(10)]
    data = generate_df(columns, index=range(100))
    response = await DataFrameRender.df_render(data, GetDataParams(
        describe=True, limit=None, curves=None, offset=None))

    assert response['columns'] == columns
    assert response['numberOfRows'] == 100


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

    actual_df = await get_df_from_request(request)
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
        await get_df_from_request(request)
    exception = ex_info.value
    assert exception.status_code == status
