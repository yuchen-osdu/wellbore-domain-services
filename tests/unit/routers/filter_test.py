import pytest

from app.bulk_persistence import GetDataParams, \
    BulkReadFilterOperator, BulkReadFilters, FilterError


@pytest.mark.parametrize("filters, expected", [
    (['A:lt:3'], [('A', BulkReadFilterOperator.Less, '3')]),
    (['"A:123":lt:3'], [('A:123', BulkReadFilterOperator.Less, '3')]),
    (['A:lt:'], [('A', BulkReadFilterOperator.Less, '')]),
    (['A:lt:3++'], [('A', BulkReadFilterOperator.Less, '3++')]),
    (['A:lt::'], [('A', BulkReadFilterOperator.Less, ':')]),
    (['A:lt:5', 'B:gt:6'], [('A', BulkReadFilterOperator.Less, '5'), ('B', BulkReadFilterOperator.Greater, '6')]),
    (['A:lt:5', 'A:gt:3'], [('A', BulkReadFilterOperator.Less, '5'), ('A', BulkReadFilterOperator.Greater, '3')]),
])
def test_parse_filter_without_exception(filters, expected):
    assert list(GetDataParams(bulk_filter=filters).get_bulk_filters()) == expected


@pytest.mark.parametrize("filters, exec_info", [
    ('A:custom_op:3', 'Invalid filter expression'),
    ('A::', 'Invalid filter expression'),
    ('A:lt', 'Invalid filter expression'),
    ('A:', 'Invalid filter expression'),
    ('A', 'Invalid filter expression'),
])
def test_parse_filter_with_exception(filters, exec_info):
    with pytest.raises(FilterError) as execinfo:
        list(GetDataParams(bulk_filter=[filters]).get_bulk_filters())
    assert exec_info in str(execinfo.value)


def test_bulk_filter_duplicate_operation():
    params = GetDataParams(bulk_filter=['A:eq:2', 'A:eq:3'])
    with pytest.raises(FilterError) as exec_info:
        BulkReadFilters(params.get_bulk_filters())
    assert 'Same operator on the same column' in str(exec_info.value)


def test_bulk_filter_conflicting_operation():
    params = GetDataParams(bulk_filter=['A:eq:3', 'A:in:1,2,3'])
    with pytest.raises(FilterError) as exec_info:
        BulkReadFilters(params.get_bulk_filters())

    assert "Operator 'eq' and 'in' can't be applied on the same column" in str(exec_info.value)


def test_bulk_filter_no_filter():
    params = GetDataParams(bulk_filter=None)
    filters = BulkReadFilters(params.get_bulk_filters())
    assert not filters.has_filter()
    assert list(filters.all_filters()) == []


def test_bulk_filter_iterate_all():
    filter_list = [('A', BulkReadFilterOperator.Less, '5'), ('B', BulkReadFilterOperator.Greater, '6')]
    filters = BulkReadFilters(filter_list)
    assert list(filters.all_filters()) == filter_list
    assert filters.columns == {'A', 'B'}
