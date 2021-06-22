import pytest

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
