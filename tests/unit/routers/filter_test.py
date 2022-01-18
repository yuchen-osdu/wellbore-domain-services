import pytest

from app.bulk_persistence.dask.errors import FilterError
from app.model.filter import parse_filter, get_parsed_filters


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
    assert exec_info in str(execinfo.value)


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
    assert exec_info in str(execinfo.value)
