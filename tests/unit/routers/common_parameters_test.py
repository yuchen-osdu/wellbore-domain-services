from unittest.mock import Mock, PropertyMock
import pytest
from fastapi import HTTPException
from app.bulk_persistence import MimeTypes
from app.routers.common_parameters import read_bulk_accept_type


@pytest.mark.parametrize("value,expected", [
    # default is parquet
    (None, MimeTypes.PARQUET),
    ("", MimeTypes.PARQUET),

    # explicit accept value
    ("application/x-parquet", MimeTypes.PARQUET),
    ("application/parquet", MimeTypes.PARQUET),
    ("application/json", MimeTypes.JSON),

    # in case of multiple, prioritize parquet
    ("application/json, application/x-parquet", MimeTypes.PARQUET),
    ("application/json, */*", MimeTypes.PARQUET),
    ("*/*", MimeTypes.PARQUET)
])
def test_read_bulk_accept_type(value, expected):
    request_mock = Mock()
    type(request_mock).headers = PropertyMock(return_value={'Accept': value})
    assert read_bulk_accept_type(request_mock) == expected


def test_explicit_unsupported_accept_raise():
    request_mock = Mock()
    type(request_mock).headers = PropertyMock(return_value={'Accept': 'text/csv'})
    with pytest.raises(HTTPException) as ex_info:
        read_bulk_accept_type(request_mock)
    exception = ex_info.value
    assert exception.status_code == 400
