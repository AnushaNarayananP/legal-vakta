from src.utils.gsheets_logger import (
    FEEDBACK_HEADERS,
    QUERY_HEADERS,
    calculate_usage_stats,
)


def test_calculate_usage_stats_handles_empty_records():
    assert calculate_usage_stats([], []) == {
        "total_queries": 0,
        "unique_users": 0,
        "total_feedback": 0,
        "useful_feedback_percent": 0.0,
        "not_useful_feedback_percent": 0.0,
    }


def test_calculate_usage_stats_counts_users_and_feedback_percentages():
    query_records = [
        {"user_id": "u1", "query": "q1"},
        {"user_id": "u2", "query": "q2"},
        {"user_id": "u1", "query": "q3"},
    ]
    feedback_records = [
        {"user_id": "u1", "feedback": "useful"},
        {"user_id": "u2", "feedback": "not_useful"},
        {"user_id": "u1", "feedback": "useful"},
    ]

    assert calculate_usage_stats(query_records, feedback_records) == {
        "total_queries": 3,
        "unique_users": 2,
        "total_feedback": 3,
        "useful_feedback_percent": 66.7,
        "not_useful_feedback_percent": 33.3,
    }


def test_sheet_headers_match_tracking_contract():
    assert QUERY_HEADERS == ["timestamp", "user_id", "name", "role", "query"]
    assert FEEDBACK_HEADERS == [
        "timestamp",
        "user_id",
        "name",
        "role",
        "query",
        "feedback",
    ]
