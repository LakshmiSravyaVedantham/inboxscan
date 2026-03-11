from inboxscan.connector import build_search_query


def test_build_search_query_returns_string():
    query = build_search_query()
    assert isinstance(query, str)
    assert len(query) > 0


def test_build_search_query_contains_receipt():
    query = build_search_query()
    assert "receipt" in query.lower()
