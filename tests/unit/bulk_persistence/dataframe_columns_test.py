import pytest

from app.bulk_persistence.dataframe_columns import (
    group_curve_columns,
    match_full_slice_pattern,
    get_array_columns,
    sort_column_labels
)


@pytest.mark.parametrize("column_labels, include_non_array, expected", [
    # empty should return empty
    ({}, True, {}),
    ({}, False, {}),

    # basic cases, non array excluded
    (['A', 'B', 'C[0]', 'C[1]', 'D[0]', 'D[1]', 'D[2]'], False,
        {'C': ['C[0]', 'C[1]'], 'D': ['D[0]', 'D[1]', 'D[2]']}),

    (['A', 'B', 'C'], False,
        {}),

    # basic cases, non array included
    (['A', 'B', 'C[0]', 'C[1]', 'D[0]', 'D[1]', 'D[2]'], True,
        {'A': ['A'], 'B': ['B'], 'C': ['C[0]', 'C[1]'], 'D': ['D[0]', 'D[1]', 'D[2]']}),

    (['A', 'B', 'C'], True,
     {'A': ['A'], 'B': ['B'], 'C': ['C']}),

    # check order is reserved
    (['C[9]', 'C[1]', 'C[100]', 'C[7]'], False,
     {'C': ['C[9]', 'C[1]', 'C[100]', 'C[7]']}),
])
def test_group_curve_columns_basic(column_labels, include_non_array, expected):
    assert group_curve_columns(column_labels, include_non_array) == expected
    if include_non_array:
        # ensure default contains non array curves
        assert group_curve_columns(column_labels) == expected
    else:
        # ensure get_array_columns filters out non array curves
        assert get_array_columns(column_labels) == expected


def test_group_curve_columns_include_non_array_by_default():
    assert 'A' in group_curve_columns(['A', 'B[0]', 'B[1]'])


def test_group_curve_columns_handle_one_million_columns():
    size = 1_000_000

    # one giant array
    r = group_curve_columns((f'C[{i}]' for i in range(size)), True)
    assert len(r['C']) == size

    # many non array
    r = group_curve_columns((f'C{i}' for i in range(size)), True)
    assert len(r) == size

    # many big arrays
    r = group_curve_columns((f'C{j}[{i}]' for i in range(int(size/1000)) for j in range(1000)), True)
    assert len(r) == 1000
    assert len(r['C500']) == 1000


@pytest.mark.parametrize("column_label, expected", [
    ('C[0:10]', ('C', '0', '10')),
    ('C', (None, None, None)),
    ('C[0]', (None, None, None)),
    ('C[0:]', (None, None, None)),
    ('C[:10]', (None, None, None)),
])
def test_match_full_slice_pattern(column_label, expected):
    assert match_full_slice_pattern(column_label) == expected


def test_sort_column_label():
    assert sort_column_labels(
        ['A', 'C[10]', 'C[20]', 'C[1]', 'Z', 'C[2]']
    ) == ['A', 'C[1]', 'C[2]', 'C[10]', 'C[20]', 'Z']
