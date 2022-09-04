import re
from contextlib import suppress
from typing import Iterable, Dict, List, Tuple, Optional, Set

from natsort import natsorted

re_column_array = re.compile(r'^(?P<name>.+)\[(?P<start>[^:]+):?(?P<stop>.*)\]$')


def group_curve_columns(all_columns=Iterable[str], include_non_array=True) -> Dict[str, List[str]]:
    """
    check column name/label to detect and group array.
    :param all_columns: column
    :param include_non_array: the `False` (default) the result does not include column that are not array
    :return: Dictionary curve name to column name/lablel. The column lists preserve the order from the input.

    Example with `include_non_array` at `False` (default), i.e. non array not included
    >>> group_curve_columns(['A', 'B', 'C[0]', 'C[1]', 'D[0]', 'D[1]', 'D[2]'], False)
    {'C': ['C[0]', 'C[1]'], 'D': ['D[0]', 'D[1]', 'D[2]']}

    Example with `include_non_array` at `True` (default), i.e. non array included
    >>> group_curve_columns(['A', 'B', 'C[0]', 'C[1]', 'D[0]', 'D[1]', 'D[2]'], True)
    {'A': ['A'], 'B': ['B'], 'C': ['C[0]', 'C[1]'], 'D': ['D[0]', 'D[1]', 'D[2]']}
    """

    array_col = {}
    for c in all_columns:
        match_result = re_column_array.match(c)
        if match_result:
            array_col.setdefault(match_result['name'], []).append(c)
        elif include_non_array:
            array_col[c] = [c]
    return array_col


def get_array_columns(all_columns=Iterable[str]) -> Dict[str, List[str]]:
    """
     returns array curves only (non curve array are filtered out) and all associated columns.
     The returned object is an array 'curve name' <-> list of columns labels
     """
    return group_curve_columns(all_columns, False)


def match_full_slice_pattern(column_label: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    match single column label to a full slice. Always return a tuple
    if not an array like or no full slice pattern return `None`, `None`, `None`
    if match an array then return a tuple, first `name`, second `start`, third `stop`

    example full slice pattern
    >>> match_full_slice_pattern('C[0:10]')
    ('C', '0', '10')

    example non array nor partial slice
    >>> match_full_slice_pattern('C')
    (None, None, None)
    >>> match_full_slice_pattern('C[0]')
    (None, None, None)
    >>> match_full_slice_pattern('C[0:]')
    (None, None, None)
    >>> match_full_slice_pattern('C[:10]')
    (None, None, None)
    """

    match_result = re_column_array.match(column_label)
    if match_result is None:
        return None, None, None  # i.e. not a slice pattern

    start, stop = match_result['start'], match_result['stop']
    if start and stop:
        return match_result['name'], start, stop
    return None, None, None  # not a full slice pattern


ColumnSelection = List[str]
""" List of column/curve. Support (full) slice notation. """


def select_columns(column_selection: ColumnSelection, columns: Set[str]) -> Tuple[List[str], List[str]]:
    """
    filter columns given a list of selection. If one selection match a curve array, the result will contains all
    associated columns. Support (full) slice notation.
    Returns two lists, the first contains the selected columns, the second contain selection that doesn't match any
    columns:

    basic example:
    >>> select_columns(['A', 'C'], {'A', "B", "C", "D"})
    (['A', 'C'], [])

    with non matching selection:
    >>> select_columns(['A', 'X'], {'A', "B", "C", "D"})
    (['A'], ['X'])

    selection a curve array:
    >>> select_columns(['A'], {'A[0]', "A[1]", "A[2]", "D"})
    (['A[0]', 'A[1]', 'A[2]'], [])

    array slicing
    >>> select_columns(['A[2:4]'], {'A[0]', "A[1]", "A[2]", "A[3]", "A[4]", "A[5]", "A[6]"})
    (['A[2]', 'A[3]', 'A[4]'], [])
    """
    selected = {}
    curves_non_existent = []
    curves_array = None

    for sel in column_selection:
        if sel in columns:
            selected[sel] = 1
            continue

        if curves_array is None:
            curves_array = get_array_columns(columns)

        matching_columns = [sel]
        curve_name_slice, slice_start, slice_stop = match_full_slice_pattern(sel)
        if curve_name_slice:
            # means sel is a form CURVE_NAME[VALUE or SLICE],
            if slice_start and slice_stop:  # full slice expression provided
                with suppress(ValueError):  # suppress int conversion exceptions
                    # TODO we may want to support floating point values ?
                    matching_columns = columns.intersection(
                        (f'{curve_name_slice}[{i}]'
                         for i in range(int(slice_start), int(slice_stop) + 1))
                    )
        if sel in curves_array:  # no slicing + known as array => add all of them
            matching_columns = curves_array[sel]

        if not columns.issuperset(matching_columns):
            curves_non_existent.extend(set(matching_columns).difference(columns))
        else:
            # TODO natsorted could be a bottleneck for big array (> 100 000)
            selected.update({column: 1 for column in natsorted(matching_columns)})

    return list(selected.keys()), curves_non_existent
