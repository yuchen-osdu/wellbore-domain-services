from typing import Tuple, Callable
import re

import pandas as pd
from pandas import DataFrame as PandasDataframe

from app.bulk_persistence.dask.errors import BulkNotProcessable

ValidationResult = Tuple[bool, str]
ValidationSuccess = (True, '')

DataframeType = PandasDataframe  # Union[PandasDataframe, DaskDataFrame]
# TODO for now, only supports validation on Pandas dataframe, need to accept Dask dataframe as input as well?

DataFrameValidationFunc = Callable[[DataframeType], ValidationResult]


def assert_df_validate(df: DataframeType,
                       validator_func: DataFrameValidationFunc,
                       *other_validator_funcs):
    """ call one or more validation function and throw BulkNotProcessable in case of invalid, run all validation before
     returning """
    validation_funcs = [validator_func, *other_validator_funcs]
    all_validity, all_reasons = zip(*[fn(df) for fn in validation_funcs])

    if not all(all_validity):
        # raise exception with all invalid reasons
        raise BulkNotProcessable(message=",".join([msg for ok, msg in zip(all_validity, all_reasons) if not ok]))


# the following functions are stateless and without side-effect so can be easily used in parallel/cross process context

def no_validation(_) -> ValidationResult:
    """
    Always validate the given dataframe without error/warning
    return True, ''
    """
    return ValidationSuccess


def auto_cast_columns_to_string(df: DataframeType) -> ValidationResult:
    """
    If given dataframe contains columns name which is not a string, cast it
    return always returns validation success
    """
    df.columns = df.columns.astype(str)
    return ValidationSuccess


def columns_type_must_be_string(df: DataframeType) -> ValidationResult:
    """ Ensure given dataframe contains columns name as string only as described by WellLog schemas """
    if all((type(t) is str for t in df.columns)):
        return ValidationSuccess

    return False, 'All columns type should be string'


def validate_index(df: DataframeType) -> ValidationResult:
    """ Ensure index """
    if len(df.index) == 0:
        return False, "Empty data"
    if not df.index.is_numeric() and not isinstance(df.index, pd.DatetimeIndex):
        return False, "Index should be numeric or datetime"
    if not df.index.is_unique:
        return False, "Duplicated index found"
    return ValidationSuccess


def columns_not_in_reserved_names(df: DataframeType) -> ValidationResult:
    """
        There are reserved name for columns which are internally used by Pandas/Dask with PyArrow to save the index.
        Save a df containing reserved name as regular columns lead to inability to read parquet file then.

        At the stage, columns used as index are already marked as index and it's not considered as columns by Pandas.
    """
    df_columns = set(df.columns)
    pyarrow_reserved_columns_found = list(filter(lambda v: re.match(r'__index_level_\d+__', v), df_columns))

    if pyarrow_reserved_columns_found:
        return False, f'Invalid column name: {",".join(pyarrow_reserved_columns_found)}'

    if '__null_dask_index__' in df_columns:
        return False, f'Invalid column name: __null_dask_index__'
    return ValidationSuccess
