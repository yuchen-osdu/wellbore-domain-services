import math

import numpy as np
import pandas as pd
import pytest
from pandas._testing import assert_frame_equal

from app.bulk_persistence.dask.errors import FilterError
from app.model.filter import parse_filter, get_parsed_filters
from tests.unit.routers.chunking_test import _create_record, Definitions, _create_df_from_response, setup_client, dasked_test_app, init_fixtures
from tests.unit.test_utils import nope_logger_fixture
from starlette.testclient import TestClient


@pytest.fixture()
def dataframe_for_filters():
    dic = {
        "A": range(20),
        "B": np.arange(20.0),
        "C": [str(i) for i in range(20)],
        "D": [i%2 == 0 for i in range(20)]
    }
    return pd.DataFrame(dic, index=range(20))


@pytest.mark.parametrize("entity_type", ['WellLog', 'Log'])
@pytest.mark.parametrize("params, expected", [
    (['A:lt:5'], lambda df: df.loc[df['A'] < 5]),
    (['A:lte:5'], lambda df: df.loc[df['A'] <= 5]),
    (['A:eq:5'], lambda df: df.loc[df['A'] == 5]),
    (['A:neq:5'], lambda df: df.loc[df['A'] != 5]),
    (['A:gt:5'], lambda df: df.loc[df['A'] > 5]),
    (['A:gte:5'], lambda df: df.loc[df['A'] >= 5]),
    (['A:in:5,6,7'], lambda df: df.loc[df['A'].isin([5, 6, 7])]),
    (['B:lt:5.0'], lambda df: df.loc[df['B'] < 5.0]),
    (['B:lte:5.0'], lambda df: df.loc[df['B'] <= 5.0]),
    (['B:eq:5.0'], lambda df: df.loc[df['B'] == 5.0]),
    (['B:neq:5.0'], lambda df: df.loc[df['B'] != 5.0]),
    (['B:gt:5.0'], lambda df: df.loc[df['B'] > 5.0]),
    (['B:gte:5.0'], lambda df: df.loc[df['B'] >= 5.0]),
    (['B:in:5.0,6.0,7.0'], lambda df: df.loc[df['B'].isin([5.0, 6.0, 7.0])]),
    (['C:gt:5'], lambda df: df.loc[df['C'] > '5']),
    (['C:gte:5'], lambda df: df.loc[df['C'] >= '5']),
    (['C:gte:5s+++'], lambda df: df.loc[df['C'] >= '5s+++']),
    (['C:eq:sss'], lambda df: df.loc[df['C'] >= 'sss']),
    (['C:lt:5'], lambda df: df.loc[df['C'] < '5']),
    (['C:lte:5'], lambda df: df.loc[df['C'] <= '5']),
    (['C:eq:5'], lambda df: df.loc[df['C'] == '5']),
    (['C:neq:5'], lambda df: df.loc[df['C'] != '5']),
    (['C:in:5,6,7'], lambda df: df.loc[df['C'].isin(['5', '6', '7'])]),
    (['C:eq:abc:def'], lambda df: df.loc[df['C'] == 'abc:def']),
    (['D:eq:True'], lambda df: df.loc[df['D'] == True]),
    (['D:neq:True'], lambda df: df.loc[df['D'] != True]),
    (['D:eq:False'], lambda df: df.loc[df['D'] == False]),
    (['A:lt:5', 'B:gte:5.0', 'D:eq:True'], lambda df: df.loc[(df['A'] < 5) & (df['B'] >= 5.0) & (df['D'] == True)]),
    (['A:lt:5', 'B:lte:5.0', 'D:eq:True'], lambda df: df.loc[(df['A'] < 5) & (df['B'] <= 5.0) & (df['D'] == True)])
])
def test_get_bulk_data_with_filters(setup_client, entity_type, params, expected, dataframe_for_filters):
    client = setup_client
    record_id = _create_record(client, entity_type)
    headers = {'content-type': 'application/x-parquet'}
    chunking_url = Definitions[entity_type]['chunking_url']
    response_send_data = client.post(f'{chunking_url}/{record_id}/data',
                                   data=dataframe_for_filters.to_parquet(engine="pyarrow"), headers=headers)
    assert response_send_data.status_code == 200

    header_get_data = {'Accept': 'application/parquet'}

    response_get_data = client.get(f'{chunking_url}/{record_id}/data', headers=header_get_data,
               params={'filter': params})
    df = _create_df_from_response(response_get_data)
    assert_frame_equal(df, expected(dataframe_for_filters))


@pytest.mark.parametrize("entity_type", ['WellLog', 'Log'])
@pytest.mark.parametrize("filter, limit, expected", [(['A:gt:5'], 5, lambda df: df.loc[df['A'] > 5]),
                                                     (['A:lt:5'], 5, lambda df: df.loc[df['A'] < 5]),
                                                     (['C:eq:5'], 5, lambda df: df.loc[df['A'] == 5]),
                                                     (['A:lt:5', 'B:lte:5.0', 'D:eq:True'], 5, lambda df: df.loc[(df['A'] < 5) & (df['B'] <= 5.0) & (df['D'] == True)])])
def test_get_bulk_data_with_filters_curves_offset(setup_client, entity_type, filter, limit, expected, dataframe_for_filters):
    client = setup_client
    record_id = _create_record(client, entity_type)
    headers = {'content-type': 'application/x-parquet'}
    chunking_url = Definitions[entity_type]['chunking_url']
    response_send_data = client.post(f'{chunking_url}/{record_id}/data',
                                   data=dataframe_for_filters.to_parquet(engine="pyarrow"), headers=headers)
    assert response_send_data.status_code == 200

    header_get_data = {'Accept': 'application/parquet'}
    curve = ['A,B']
    for i in range(0, math.ceil(20/limit)):
        response_get_data = client.get(f'{chunking_url}/{record_id}/data', headers=header_get_data,
                   params={'filter': filter, 'curves': curve, 'offset': i*limit, 'limit': limit})
        df = _create_df_from_response(response_get_data)
        df_expected = expected(dataframe_for_filters).iloc[i*limit:(i+1)*limit][['A', 'B']]
        assert_frame_equal(df, df_expected)


@pytest.mark.parametrize("entity_type", ['WellLog', 'Log'])
@pytest.mark.parametrize("filter, limit, curves, expected", [(['A:gt:5'], 5, ['A,B'], [5, 5, 4, 0]),
                                                            (['A:lt:5'], 5, ['A,C'], [5, 0, 0, 0]),
                                                            (['D:eq:True'], 5, ['C,D'], [5, 5, 0, 0]),
                                                            (['C:in:5,6,7'], 5, ['B,D'], [3, 0, 0, 0])
                                                            ])
def test_get_bulk_data_with_filters_curves_offset_describe(setup_client, entity_type, filter, limit, expected, dataframe_for_filters, curves):
    client = setup_client
    record_id = _create_record(client, entity_type)
    headers = {'content-type': 'application/x-parquet'}
    chunking_url = Definitions[entity_type]['chunking_url']
    response_send_data = client.post(f'{chunking_url}/{record_id}/data',
                                   data=dataframe_for_filters.to_parquet(engine="pyarrow"), headers=headers)
    assert response_send_data.status_code == 200

    header_get_data = {'Accept': 'application/parquet'}
    for i in range(0, math.ceil(20/limit)):
        response_get_data = client.get(f'{chunking_url}/{record_id}/data', headers=header_get_data,
                   params={'filter': filter, 'curves': curves, 'offset': i*limit, 'limit': limit, 'describe': True})
        assert response_get_data.json()['numberOfRows'] == expected[i]
        assert response_get_data.json()['columns'] == curves[0].split(',')


@pytest.mark.parametrize("entity_type", ['WellLog', 'Log'])
@pytest.mark.parametrize("params, content", [
    (['M:lt:5'], "The columns:['M'] to be filtered do not exist"),
    (['A:xx:5'], 'Operator xx is not supported'),
    (['A:lt:5', 'A:lt:7'], 'Same operator on the same column'),
])
def test_get_bulk_data_with_filters_fail(setup_client, entity_type, params, content, dataframe_for_filters):
    client = setup_client
    record_id = _create_record(client, entity_type)
    headers = {'content-type': 'application/x-parquet'}
    chunking_url = Definitions[entity_type]['chunking_url']
    response_send_data = client.post(f'{chunking_url}/{record_id}/data',
                                   data=dataframe_for_filters.to_parquet(engine="pyarrow"), headers=headers)
    assert response_send_data.status_code == 200

    header_get_data = {'Accept': 'application/parquet'}

    response_get_data = client.get(f'{chunking_url}/{record_id}/data', headers=header_get_data,
               params={'filter': params})

    assert response_get_data.json()['detail'] == content
    assert response_get_data.status_code == 400


@pytest.mark.parametrize("filters, expected", [
    ('A:lt:3', ('A', 'lt', '3')),
    ('A:lt:', ('A', 'lt', '')),
    ('A:lt:3++', ('A', 'lt', '3++')),
    ('A:lt::', ('A', 'lt', ':')),
    ('A::', ('A', '', '')),

])
def test_parse_filter_without_exception(filters, expected):
    assert parse_filter(filters) == expected


@pytest.mark.parametrize("filters, exec_info", [
    ('A:lt', 'Invalid filter expression A:lt'),
    ('A:', 'Invalid filter expression A:'),
    ('A', 'Invalid filter expression A'),
])
def test_parse_filter_with_exception(filters, exec_info):
    with pytest.raises(FilterError) as execinfo:
        parse_filter(filters)
    assert str(execinfo.value) == exec_info


@pytest.mark.parametrize("filters, expected", [
    (['A:lt:5'], {'A': {'lt': '5'}}),
    (['A:lt:'], {'A': {'lt': ''}}),
    (['A:lt:5', 'B:gt:6'], {'A': {'lt': '5'}, 'B': {'gt': '6'}}),
    (['A:lt:5', 'A:gt:3'], {'A': {'lt': '5', 'gt': '3'}}),
])
def test_get_filters_without_exception(filters, expected):
    assert get_parsed_filters(filters) == expected


@pytest.mark.parametrize("filters, exec_info", [
    (['A:lt'], 'Invalid filter expression A:lt'),
    (['A:'], 'Invalid filter expression A:'),
    (['A'], 'Invalid filter expression A'),
    (['A:eq:2', 'A:eq:3'], 'Same operator on the same column'),
    (['A:=:2'], 'Operator = is not supported'),
    (['A:eq:3', 'A:in:1,2,3'], "Operator 'in' and 'eq' can't be applied on the same column")

])
def test_get_filters_with_exception(filters, exec_info):
    with pytest.raises(FilterError) as execinfo:
        get_parsed_filters(filters)
    assert str(execinfo.value) == exec_info
