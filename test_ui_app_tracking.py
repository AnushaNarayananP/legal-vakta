from pathlib import Path
import shutil

import pandas as pd

from src.ui.app import get_recent_unique_queries, load_usage_stats, log_query, save_feedback


def test_log_query_appends_query_with_timestamp():
    test_root = Path("test_artifacts") / "ui_tracking"
    if test_root.exists():
        shutil.rmtree(test_root)

    query_log_path = test_root / "query_logs.csv"

    log_query(
        "benefit of doubt",
        user_id="user-1",
        name="Asha",
        role="Law Student",
        email="asha@example.com",
        query_log_path=query_log_path,
    )

    df = pd.read_csv(query_log_path)
    assert df.columns.tolist() == ["timestamp", "user_id", "name", "email", "role", "query"]
    assert df["user_id"].tolist() == ["user-1"]
    assert df["name"].tolist() == ["Asha"]
    assert df["role"].tolist() == ["Law Student"]
    assert df["email"].tolist() == ["asha@example.com"]
    assert df["query"].tolist() == ["benefit of doubt"]
    assert isinstance(df.loc[0, "timestamp"], str)

    shutil.rmtree(test_root)


def test_save_feedback_appends_feedback_with_timestamp():
    test_root = Path("test_artifacts") / "ui_tracking"
    if test_root.exists():
        shutil.rmtree(test_root)

    feedback_path = test_root / "feedback.csv"

    save_feedback(
        "bail conditions",
        "useful",
        user_id="user-2",
        name="Rao",
        role="Lawyer",
        feedback_path=feedback_path,
    )

    df = pd.read_csv(feedback_path)
    assert df.columns.tolist() == [
        "timestamp",
        "user_id",
        "name",
        "role",
        "query",
        "feedback",
    ]
    assert df["user_id"].tolist() == ["user-2"]
    assert df["name"].tolist() == ["Rao"]
    assert df["role"].tolist() == ["Lawyer"]
    assert df["query"].tolist() == ["bail conditions"]
    assert df["feedback"].tolist() == ["useful"]
    assert isinstance(df.loc[0, "timestamp"], str)

    shutil.rmtree(test_root)


def test_save_feedback_ignores_email_profile_field():
    test_root = Path("test_artifacts") / "ui_tracking"
    if test_root.exists():
        shutil.rmtree(test_root)

    feedback_path = test_root / "feedback.csv"

    save_feedback(
        "circumstantial evidence",
        "not_useful",
        user_id="user-3",
        name="Meera",
        email="meera@example.com",
        role="Researcher",
        feedback_path=feedback_path,
    )

    df = pd.read_csv(feedback_path)
    assert df.columns.tolist() == [
        "timestamp",
        "user_id",
        "name",
        "role",
        "query",
        "feedback",
    ]
    assert df["user_id"].tolist() == ["user-3"]
    assert df["role"].tolist() == ["Researcher"]
    assert df["feedback"].tolist() == ["not_useful"]

    shutil.rmtree(test_root)


def test_load_usage_stats_handles_missing_files_and_counts_rows():
    test_root = Path("test_artifacts") / "ui_tracking"
    if test_root.exists():
        shutil.rmtree(test_root)

    query_log_path = test_root / "query_logs.csv"
    feedback_path = test_root / "feedback.csv"

    assert load_usage_stats(query_log_path, feedback_path) == {
        "total_queries": 0,
        "unique_users": 0,
        "total_feedback": 0,
        "useful_feedback_percent": 0.0,
        "not_useful_feedback_percent": 0.0,
    }

    log_query("query one", "user-1", "Asha", "Law Student", "asha@example.com", query_log_path=query_log_path)
    log_query("query two", "user-2", "", "Researcher", "", query_log_path=query_log_path)
    query_df = pd.read_csv(query_log_path, keep_default_na=False)
    assert query_df["email"].tolist() == ["asha@example.com", "N/A"]
    save_feedback("query one", "useful", "user-1", "Asha", "Law Student", feedback_path=feedback_path)
    save_feedback("query two", "not_useful", "user-2", "", "Researcher", feedback_path=feedback_path)

    assert load_usage_stats(query_log_path, feedback_path) == {
        "total_queries": 2,
        "unique_users": 2,
        "total_feedback": 2,
        "useful_feedback_percent": 50.0,
        "not_useful_feedback_percent": 50.0,
    }

    shutil.rmtree(test_root)


def test_get_recent_unique_queries_keeps_last_five_unique_and_truncates():
    long_query = "What reasoning is used when medical evidence contradicts eyewitness testimony?"
    history = [
        "Benefit of doubt in criminal appeals",
        long_query,
        "Circumstantial evidence cases",
        long_query,
        "Bail conditions in serious offences",
        "Delay in filing FIR",
        "Witness credibility in criminal appeals",
    ]

    result = get_recent_unique_queries(history)

    assert len(result) == 5
    assert result[0] == "Witness credibility in criminal appeals"
    assert result[1] == "Delay in filing FIR"
    assert result[2] == "Bail conditions in serious offences"
    assert result[3].endswith("...")
    assert len(result[3]) == 60
    assert result[4] == "Circumstantial evidence cases"
