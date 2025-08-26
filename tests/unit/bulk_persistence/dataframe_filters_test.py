import pytest
import pandas as pd
import numpy as np
import dask.dataframe as dd
from pandas.testing import assert_frame_equal

from app.bulk_persistence import GetDataParams
from app.bulk_persistence.dask.dataframe_render import DataFrameRender
from app.bulk_persistence.bulk_filter import BulkReadFilters


@pytest.fixture()
def dataframe_for_filters():
    dic = {
        "A": range(20),
        "B": np.arange(20.0),
        "C": [str(i) for i in range(20)],
        "D": [i % 2 == 0 for i in range(20)]
    }
    df = pd.DataFrame(dic, index=range(20))
    return df

@pytest.mark.anyio
@pytest.mark.parametrize("use_dask", [True, False])
@pytest.mark.parametrize(
    "filter_params, expected_df_lambda",
    [
        (["A:lt:5"], lambda df: df.loc[df["A"] < 5]),
        (["A:lte:5"], lambda df: df.loc[df["A"] <= 5]),
        (["A:eq:5"], lambda df: df.loc[df["A"] == 5]),
        (["A:neq:5"], lambda df: df.loc[df["A"] != 5]),
        (["A:gt:5"], lambda df: df.loc[df["A"] > 5]),
        (["A:gte:5"], lambda df: df.loc[df["A"] >= 5]),
        (["A:in:5,6,7"], lambda df: df.loc[df["A"].isin([5, 6, 7])]),
        (["B:lt:5.0"], lambda df: df.loc[df["B"] < 5.0]),
        (["B:lte:5.0"], lambda df: df.loc[df["B"] <= 5.0]),
        (["B:eq:5.0"], lambda df: df.loc[df["B"] == 5.0]),
        (["B:neq:5.0"], lambda df: df.loc[df["B"] != 5.0]),
        (["B:gt:5.0"], lambda df: df.loc[df["B"] > 5.0]),
        (["B:gte:5.0"], lambda df: df.loc[df["B"] >= 5.0]),
        (["B:in:5.0,6.0,7.0"], lambda df: df.loc[df["B"].isin([5.0, 6.0, 7.0])]),
        (["C:gt:'5'"], lambda df: df.loc[df["C"] > "5"]),
        (["C:gte:'5'"], lambda df: df.loc[df["C"] >= "5"]),
        (["C:gte:5s+++"], lambda df: df.loc[df["C"] >= "5s+++"]),
        (["C:eq:sss"], lambda df: df.loc[df["C"] == "sss"]),
        (["C:lt:'5'"], lambda df: df.loc[df["C"] < "5"]),
        (["C:lte:'5'"], lambda df: df.loc[df["C"] <= "5"]),
        (["C:eq:'5'"], lambda df: df.loc[df["C"] == "5"]),
        (["C:neq:'5'"], lambda df: df.loc[df["C"] != "5"]),
        (["C:in:'5','6','7'"], lambda df: df.loc[df["C"].isin(["5", "6", "7"])]),
        (["C:eq:abc:def"], lambda df: df.loc[df["C"] == "abc:def"]),
        (["D:eq:True"], lambda df: df.loc[df["D"] == True]),
        (["D:neq:True"], lambda df: df.loc[df["D"] != True]),
        (["D:eq:False"], lambda df: df.loc[df["D"] == False]),
        (["A:lt:5", "B:gte:5.0", "D:eq:True"], lambda df: df.loc[(df["A"] < 5) & (df["B"] >= 5.0) & (df["D"] == True)]),
        (["A:lt:5", "B:lte:5.0", "D:eq:True"], lambda df: df.loc[(df["A"] < 5) & (df["B"] <= 5.0) & (df["D"] == True)]),
    ]
)
async def test_df_with_filter(use_dask, dataframe_for_filters, filter_params, expected_df_lambda):
    params = GetDataParams(filter=filter_params)
    bulk_filters = BulkReadFilters(params.get_bulk_filters())

    if use_dask:
        df = dd.from_pandas(dataframe_for_filters, npartitions=1)
        actual_df = DataFrameRender.apply_filter(df, bulk_filters).compute()
    else:
        actual_df = DataFrameRender.apply_filter(dataframe_for_filters, bulk_filters)

    expected_df = expected_df_lambda(dataframe_for_filters)

    assert_frame_equal(expected_df, actual_df, check_dtype=False)
