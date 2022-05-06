from typing import Tuple, Callable, Iterable, List
import re

import pandas as pd

from .dask.utils import WDMS_INDEX_NAME


ValidationResult = Tuple[bool, str]  # Tuple (is_dataframe_valid, failure_reason)

ValidationSuccess = (True, '')

DataFrameValidationFunc = Callable[[pd.DataFrame], ValidationResult]


def no_validation(_) -> ValidationResult:
    """
    Always validate the given dataframe without error/warning
    return True, ''
    """
    return ValidationSuccess


def make_multi_validator(validation_funcs: List[DataFrameValidationFunc]) -> DataFrameValidationFunc:
    if not validation_funcs:
        return no_validation

    def _multi_validate(dataframe: pd.DataFrame):
        all_validity, all_reasons = zip(*[fn(dataframe) for fn in validation_funcs])
        return all(all_validity), ",".join([msg for ok, msg in zip(all_validity, all_reasons) if not ok])

    return _multi_validate

# the following functions are stateless and without side-effect so can be easily used in parallel/cross process context


def auto_cast_columns_to_string(df: pd.DataFrame) -> ValidationResult:
    """
    If given dataframe contains columns name which is not a string, cast it
    return always returns validation success
    """
    df.columns = df.columns.astype(str)
    return ValidationSuccess


def columns_type_must_be_string(df: pd.DataFrame) -> ValidationResult:
    """ Ensure given dataframe contains columns name as string only as described by WellLog schemas """
    if all((type(t) is str for t in df.columns)):
        return ValidationSuccess
    return False, 'All columns type should be string'


def validate_index(df: pd.DataFrame) -> ValidationResult:
    """ Ensure index """
    if len(df.index) == 0:
        return False, "Empty data"
    if not df.index.is_numeric() and not isinstance(df.index, pd.DatetimeIndex):
        return False, "Index should be numeric or datetime"
    if not df.index.is_unique:
        return False, "Duplicated index found"
    return ValidationSuccess


def make_number_of_columns_validator(max_number_column) -> DataFrameValidationFunc:
    def validate_number_of_columns(df: pd.DataFrame) -> ValidationResult:
        """ Verify max number of columns """
        if len(df.columns) > max_number_column:
            return False, f"Too many columns : maximum allowed '{max_number_column}'"
        return ValidationSuccess
    return validate_number_of_columns


PandasReservedIndexColRegexp = re.compile(r'__index_level_\d+__')


def is_reserved_column_name(name: str) -> bool:
    """Return True if the name is a reserved column name by Pandas/Dask with PyArrow"""
    return (PandasReservedIndexColRegexp.match(name)
            or name == '__null_dask_index__'
            or name == WDMS_INDEX_NAME)


def any_reserved_column_name(names: Iterable[str]) -> bool:
    """
        There are reserved name for columns which are internally used by Pandas/Dask with PyArrow to save the index.
        Save a df containing reserved name as regular columns lead to inability to read parquet file then.

        At this stage, columns used as index are already marked as index and it's not considered as columns by Pandas.
        return: True is any column uses a reserved name
    """
    return any(is_reserved_column_name(name) for name in names if type(name) is str)


def columns_not_in_reserved_names(df: pd.DataFrame) -> ValidationResult:
    if any_reserved_column_name(df.columns):
        return False, 'Invalid column name'

    return ValidationSuccess
