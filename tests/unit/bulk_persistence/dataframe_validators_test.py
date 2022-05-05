import datetime

import pytest
import pandas as pd
from unittest.mock import Mock

from app.bulk_persistence.dataframe_validators import (
    no_validation,
    auto_cast_columns_to_string,
    columns_type_must_be_string,
    columns_not_in_reserved_names,
    any_reserved_column_name,
    validate_index,
    assert_df_validate,
    validate_number_of_columns
)

from app.bulk_persistence.dask.errors import BulkNotProcessable
from app.bulk_persistence import setup_bulk_persistence


def test_no_validation_always_success():
    result, error_reason = no_validation(None)
    assert result
    assert not error_reason


@pytest.mark.parametrize("input_data", [
    {},
    {'1': [10], '2': [20]},
    {'1': [10], 2: [20]},
    {1: [10], 2: [20]},
])
def test_auto_cast_columns_to_string(input_data):
    df = pd.DataFrame(input_data)

    actual_result, _ = auto_cast_columns_to_string(df)
    assert actual_result
    assert all((type(t) is str for t in df.columns))


@pytest.mark.parametrize("input_data, expected_result, expected_reason", [
    ({}, True, ''),
    ({'1': [10], '2': [20]}, True, ''),
    ({'1': [10], 2: [20]}, False, 'All columns type should be string'),
    ({1: [10], 2: [20]}, False, 'All columns type should be string'),
])
def test_columns_type_must_be_string(input_data, expected_result, expected_reason):
    df = pd.DataFrame(input_data)

    actual_result, actual_reason = columns_type_must_be_string(df)
    assert actual_result == expected_result
    assert actual_reason == expected_reason


@pytest.mark.parametrize("reserved_columns_name", ['__index_level_0__', '__null_dask_index__'])
@pytest.mark.parametrize("use_custom_index", [True, False])
def test_df_with_reserved_name_should_be_invalid(reserved_columns_name, use_custom_index):

    # A column named '__index_level_0__' is internally used by PyArrow to save the index.
    # Sending column named the same way as regular column causes problems to read them with Dask.
    df = pd.DataFrame({'float-COLUMN_MD': [10.1], 'COLUMN_X': [20], reserved_columns_name: [30]})

    if use_custom_index:
        df = df.set_index('float-COLUMN_MD')

    is_valid, actual_reason = columns_not_in_reserved_names(df)
    assert not is_valid
    assert actual_reason


def test_invalid_index():
    input_data = {
        'not_int': ['a', 'b'],
        'not_unique': [1, 1]
    }

    for column_name in input_data.keys():
        df = pd.DataFrame(input_data).set_index(column_name)
        is_valid, actual_reason = validate_index(df)
        assert not is_valid
        assert actual_reason


def test_valid_index():
    input_data = {
        'increasing_int': [1, 2, 3],
        'decreasing_int': [3, 2, 1],
        'increasing_float': [1.1, 2.2, 3.3],
        'datetime_index': [datetime.datetime(2000, 1, 1), datetime.datetime(2000, 1, 2), datetime.datetime(2000, 1, 3)]
    }

    for column_name in input_data.keys():
        df = pd.DataFrame(input_data).set_index(column_name)
        is_valid, _ = validate_index(df)
        assert is_valid


def test_assert_df_validate_empty_succeed():
    assert_df_validate(pd.DataFrame(), [])


def test_assert_df_validate_single():
    validation_fn = Mock(return_value=(True, "validation ok"))
    assert_df_validate(pd.DataFrame(), [validation_fn])
    validation_fn.assert_called_once()


def test_validators_composition_success():
    df = pd.DataFrame({'A': [10], 'B': [20]}).set_index('A')
    assert_df_validate(df, [validate_index, columns_not_in_reserved_names])


def test_validators_composition():
    # GIVEN 3 validations
    validation_1 = Mock(return_value=(False, "validation1"))
    validation_2 = Mock(return_value=(False, "validation2"))
    validation_3 = Mock(return_value=(True, "validation3"))

    # WHEN
    with pytest.raises(BulkNotProcessable) as ex_info:
        assert_df_validate(pd.DataFrame(), [validation_1, validation_2, validation_3])

    # THEN all validations where called
    validation_1.assert_called_once()
    validation_2.assert_called_once()
    validation_3.assert_called_once()

    # and THEN error contains only failed reason
    error_msg = str(ex_info.value)
    assert "validation1" in error_msg
    assert "validation2" in error_msg
    assert "validation3" not in error_msg


@pytest.mark.parametrize("columns,expected", [
    # valid cases
    (["A", "B"], False),
    (["__index_level_A__", "B"], False),

    # invalid cases with reserved name
    (["A", "__index_level_0__"], True),
    (["__index_level_1__", "B"], True),
    (["__null_dask_index__", "B"], True)
])
def test_any_reserved_column_name(columns, expected):
    assert any_reserved_column_name(columns) == expected

@pytest.mark.parametrize("limit,nb_col,expected", [
    (100, 50, True),
    (100, 100, True),
    (100, 101, False),
    (50, 100, False),
])
def test_validate_number_of_columns(limit, nb_col, expected, local_bulk_persistence_config):

    local_bulk_persistence_config.max_columns_per_chunk_write = limit

    columns = [f'col_{i}' for i in range(nb_col)]
    result, _info = validate_number_of_columns(pd.DataFrame(columns=columns))
    assert result == expected
