import pytest

import app.routers.search.search_v3_wellbore as search_v3_wellbore
import app.routers.search.search_v3 as search_v3

ADDED_QUERY_PARAMS = [
    (None, None, None),
    ("Generated query", None, "Generated query"),
    (None, "User query", "None AND (User query)"),
    ("Generated query", "User query", "Generated query AND (User query)"),
]


@pytest.mark.parametrize("generated_query, user_query, expected_query", ADDED_QUERY_PARAMS)
def test_added_query(generated_query, user_query, expected_query):
    assert search_v3.added_query(generated_query, user_query) == expected_query


ADDED_QUERY_PARAMS = [
    (None, None, None),
    ("Generated query", None, "Generated query"),
    (None, "User query", "None AND (User query)"),
    ("Generated query", "User query", "Generated query AND (User query)"),
]

RELATIONSHIPS_QUERY_PARAMS = [
    ("thiscouldbeanid", None, "data.WellboreID:\"thiscouldbeanid\""),
    ("thiscouldbeanid", "user query", "data.WellboreID:\"thiscouldbeanid\" AND (user query)"),
]


@pytest.mark.parametrize("id, user_query, expected_query", RELATIONSHIPS_QUERY_PARAMS)
def test_added_relationships_query(id, user_query, expected_query):
    assert search_v3.added_relationships_query(id, 'WellboreID', user_query) == expected_query


NAMES_QUERY_PARAMS = [
    (None, None, 'data.FacilityName:None'),
    ('Fab OR Fred', None, 'data.FacilityName:Fab OR Fred'),
    ('Fab', 'data.AnyField:\\"any value\\"', 'data.FacilityName:Fab AND (data.AnyField:\\"any value\\")'),
]


@pytest.mark.parametrize("names, user_query, expected_query", NAMES_QUERY_PARAMS)
def test_update_query_with_names_based_search(names, user_query, expected_query):
    assert search_v3_wellbore.update_query_with_names_based_search(names, user_query) == expected_query


ESCAPE_CHAR_PARAMS = [
    ('', ''),
    ('not char to escape', 'not char to escape'),
    ('wildcard * ? not to escape', 'wildcard * ? not to escape'),
    (r'all other to escape +-=><!(){}[]^"~:\ /', r'all other to escape \+\-\=\>\<\!\(\)\{\}\[\]\^\"\~\:\\ \/'),
]


@pytest.mark.parametrize("input_str, expected_str", ESCAPE_CHAR_PARAMS)
def test_escape_forbidden_characters_for_search(input_str, expected_str):
    assert search_v3_wellbore.escape_forbidden_characters_for_search(input_str) == expected_str
