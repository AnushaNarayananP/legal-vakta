from pathlib import Path
import shutil

import pandas as pd

from src.ui.app import (
    build_impact_stats,
    clear_session_user_id,
    consume_pending_query_event,
    embed_inline_html,
    get_feedback_key,
    get_feedback_state,
    get_active_prompt_and_source,
    get_confidence_label,
    get_persistent_user_id,
    get_prompt_source,
    get_query_param_user_id,
    get_recent_unique_queries,
    get_user_facing_error_message,
    load_usage_stats,
    log_generated_query,
    log_query,
    mark_feedback_submitted,
    queue_suggested_query,
    QUERY_SOURCE_CHATBOT,
    QUERY_SOURCE_MANUAL_TEST,
    QUERY_SOURCE_MODE_REGENERATION,
    QUERY_SOURCE_SUGGESTED,
    save_feedback,
    update_feedback_state,
)


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
        answer_mode="Legal",
        confidence="High",
        query_log_path=query_log_path,
    )

    df = pd.read_csv(query_log_path)
    assert df.columns.tolist() == [
        "timestamp",
        "user_id",
        "query",
        "role",
        "answer_mode",
        "confidence",
        "source",
    ]
    assert df["user_id"].tolist() == ["user-1"]
    assert df["role"].tolist() == ["Law Student"]
    assert df["answer_mode"].tolist() == ["Legal"]
    assert df["query"].tolist() == ["benefit of doubt"]
    assert df["confidence"].tolist() == ["High"]
    assert df["source"].tolist() == ["chatbot_query"]
    assert isinstance(df.loc[0, "timestamp"], str)

    shutil.rmtree(test_root)


def test_log_query_allows_manual_test_source():
    test_root = Path("test_artifacts") / "ui_tracking"
    if test_root.exists():
        shutil.rmtree(test_root)

    query_log_path = test_root / "query_logs.csv"

    log_query(
        "manual smoke query",
        user_id="dev-user",
        role="Researcher",
        answer_mode="Student",
        confidence="Low",
        source=QUERY_SOURCE_MANUAL_TEST,
        query_log_path=query_log_path,
    )

    df = pd.read_csv(query_log_path)
    assert df["answer_mode"].tolist() == ["Student"]
    assert df["source"].tolist() == [QUERY_SOURCE_MANUAL_TEST]

    shutil.rmtree(test_root)


def test_get_prompt_source_distinguishes_typed_and_suggested_queries():
    assert get_prompt_source("typed question", None) == QUERY_SOURCE_CHATBOT
    assert get_prompt_source("", "Benefit of doubt in criminal appeals") == QUERY_SOURCE_SUGGESTED
    assert get_prompt_source(None, "Benefit of doubt in criminal appeals") == QUERY_SOURCE_SUGGESTED
    assert get_prompt_source("", None) == QUERY_SOURCE_CHATBOT


def test_get_active_prompt_and_source_prefers_clicked_suggestion_when_both_inputs_exist():
    prompt, source = get_active_prompt_and_source(
        "stale typed prompt",
        "Benefit of doubt in criminal appeals",
    )

    assert prompt == "Benefit of doubt in criminal appeals"
    assert source == QUERY_SOURCE_SUGGESTED


def test_pending_suggested_query_event_resolves_as_suggested_query():
    state = {}

    queue_suggested_query(state, "Benefit of doubt in criminal appeals")
    prompt, source = consume_pending_query_event(state, typed_prompt="")

    assert prompt == "Benefit of doubt in criminal appeals"
    assert source == QUERY_SOURCE_SUGGESTED
    assert "pending_query" not in state
    assert "pending_query_source" not in state


def test_pending_suggestion_takes_priority_over_typed_prompt():
    state = {
        "pending_query": "Benefit of doubt in criminal appeals",
        "pending_query_source": QUERY_SOURCE_SUGGESTED,
    }

    prompt, source = consume_pending_query_event(state, typed_prompt="typed bail question")

    assert prompt == "Benefit of doubt in criminal appeals"
    assert source == QUERY_SOURCE_SUGGESTED
    assert "pending_query" not in state
    assert "pending_query_source" not in state


def test_log_generated_query_records_mode_regeneration_source(monkeypatch):
    calls = []

    monkeypatch.setattr(
        "src.ui.app.get_user_profile",
        lambda: {"user_id": "user-1", "name": "Asha", "role": "Law Student", "email": "asha@example.com"},
    )
    monkeypatch.setattr("src.ui.app.log_query", lambda *args, **kwargs: calls.append((args, kwargs)) or True)

    payload = {
        "result": {"retrieved_docs": [object(), object(), object(), object()]},
        "prompt": "Benefit of doubt",
        "mode": "Student",
    }

    assert log_generated_query(payload, source=QUERY_SOURCE_MODE_REGENERATION) is True
    assert calls == [
        (
            ("Benefit of doubt",),
            {
                "user_id": "user-1",
                "role": "Law Student",
                "answer_mode": "Student",
                "confidence": "High",
                "source": QUERY_SOURCE_MODE_REGENERATION,
            },
        )
    ]


def test_get_persistent_user_id_prefers_local_storage_over_different_session_id():
    state = {"user_id": "user_session-456"}

    user_id = get_persistent_user_id(
        state=state,
        local_storage_id="user_browser-123",
        generate_uuid=lambda: "new-789",
    )

    assert user_id == "user_browser-123"
    assert state["user_id"] == "user_browser-123"
    assert state["local_storage_user_id"] == "user_browser-123"


def test_get_persistent_user_id_uses_local_storage_when_session_is_empty():
    state = {}

    user_id = get_persistent_user_id(
        state=state,
        local_storage_id="user_browser-123",
        generate_uuid=lambda: "new-789",
    )

    assert user_id == "user_browser-123"
    assert state["user_id"] == "user_browser-123"
    assert state["local_storage_user_id"] == "user_browser-123"


def test_get_persistent_user_id_returns_empty_when_local_storage_is_pending():
    state = {"user_id": "user_session-456"}

    user_id = get_persistent_user_id(
        state=state,
        local_storage_id=None,
        generate_uuid=lambda: "new-789",
    )

    assert user_id == ""
    assert state["user_id"] == "user_session-456"


def test_get_persistent_user_id_does_not_create_session_fallback_when_browser_is_pending():
    state = {}

    user_id = get_persistent_user_id(
        state=state,
        local_storage_id=None,
        generate_uuid=lambda: "new-789",
    )

    assert user_id == ""
    assert "user_id" not in state
    assert "local_storage_user_id" not in state


def test_get_persistent_user_id_later_local_storage_overwrites_session_fallback():
    state = {"user_id": "user_new-789"}

    user_id = get_persistent_user_id(
        state=state,
        local_storage_id="user_browser-123",
        generate_uuid=lambda: "unused",
    )

    assert user_id == "user_browser-123"
    assert state["user_id"] == "user_browser-123"
    assert state["local_storage_user_id"] == "user_browser-123"


def test_get_persistent_user_id_uses_existing_confirmed_local_storage_session():
    state = {"user_id": "user_browser-123", "local_storage_user_id": "user_browser-123"}

    user_id = get_persistent_user_id(
        state=state,
        local_storage_id=None,
        generate_uuid=lambda: "new-789",
    )

    assert user_id == "user_browser-123"


def test_get_persistent_user_id_reads_browser_id_from_query_params():
    state = {}

    user_id = get_persistent_user_id(
        state=state,
        query_params={"spacel_user_id": "user_browser-456"},
        generate_uuid=lambda: "new-789",
    )

    assert user_id == "user_browser-456"
    assert state["user_id"] == "user_browser-456"
    assert state["local_storage_user_id"] == "user_browser-456"


def test_get_query_param_user_id_handles_streamlit_list_values():
    assert get_query_param_user_id({"spacel_user_id": ["user_browser-789"]}) == "user_browser-789"


def test_embed_inline_html_uses_javascript_enabled_st_html_when_available(monkeypatch):
    calls = []

    def fake_st_html(body, *, width="stretch", unsafe_allow_javascript=False):
        calls.append((body, width, unsafe_allow_javascript))

    monkeypatch.setattr("src.ui.app.st.html", fake_st_html, raising=False)

    embed_inline_html("<script>window.test = true;</script>", height=0)

    assert calls == [("<script>window.test = true;</script>", "stretch", True)]


def test_embed_inline_html_falls_back_to_components_html_without_javascript_option(monkeypatch):
    calls = []

    def fake_st_html(body, *, width="stretch"):
        calls.append(("st.html", body, width))

    def fake_components_html(body, **kwargs):
        calls.append(("components.html", body, kwargs))

    monkeypatch.setattr("src.ui.app.st.html", fake_st_html, raising=False)
    monkeypatch.setattr("src.ui.app.components.html", fake_components_html)

    embed_inline_html("<script>window.test = true;</script>", height=0)

    assert calls == [("components.html", "<script>window.test = true;</script>", {"height": 0})]


def test_get_persistent_user_id_ignores_name_email_role_changes():
    state = {
        "user_id": "user_browser-123",
        "user_name": "Old",
        "email": "old@example.com",
        "user_role": "Law Student",
    }

    state["user_name"] = "New"
    state["email"] = "new@example.com"
    state["user_role"] = "Lawyer"

    user_id = get_persistent_user_id(
        state=state,
        local_storage_id="user_browser-123",
        generate_uuid=lambda: "new-789",
    )

    assert user_id == "user_browser-123"


def test_clear_session_user_id_removes_identity_keys():
    state = {
        "user_id": "user-1",
        "local_storage_user_id": "user-1",
        "_last_browser_user_id": "old",
        "user_id_source": "browser",
        "other": "kept",
    }

    clear_session_user_id(state)

    assert state == {"other": "kept"}


def test_feedback_key_is_scoped_by_user_query_and_mode():
    legal_key = get_feedback_key("user-1", "Benefit of doubt", "Legal")
    student_key = get_feedback_key("user-1", "Benefit of doubt", "Student")
    different_query_key = get_feedback_key("user-1", "Bail", "Legal")
    different_user_key = get_feedback_key("user-2", "Benefit of doubt", "Legal")

    assert legal_key != student_key
    assert legal_key != different_query_key
    assert legal_key != different_user_key
    assert legal_key.startswith("user-1_")
    assert legal_key.endswith("_Legal")


def test_feedback_state_defaults_and_updates_are_isolated_by_key():
    state = {}
    legal_key = get_feedback_key("user-1", "Benefit of doubt", "Legal")
    student_key = get_feedback_key("user-1", "Benefit of doubt", "Student")

    assert get_feedback_state(state, legal_key) == {
        "rating": None,
        "text": "",
        "submitted": False,
    }

    update_feedback_state(state, legal_key, rating="helpful", text="Clear")
    mark_feedback_submitted(state, legal_key)

    assert get_feedback_state(state, legal_key) == {
        "rating": "helpful",
        "text": "Clear",
        "submitted": True,
    }
    assert get_feedback_state(state, student_key) == {
        "rating": None,
        "text": "",
        "submitted": False,
    }


def test_get_confidence_label_uses_allowed_sheet_values():
    assert get_confidence_label([object(), object(), object(), object()]) == "High"
    assert get_confidence_label([object(), object()]) == "Medium"
    assert get_confidence_label([]) == "Low"


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
        answer_mode="Legal",
        feedback_path=feedback_path,
    )

    df = pd.read_csv(feedback_path)
    assert df.columns.tolist() == [
        "timestamp",
        "user_id",
        "name",
        "role",
        "query",
        "answer_mode",
        "rating",
        "written_feedback",
        "source",
    ]
    assert df["user_id"].tolist() == ["user-2"]
    assert df["name"].tolist() == ["Rao"]
    assert df["role"].tolist() == ["Lawyer"]
    assert df["query"].tolist() == ["bail conditions"]
    assert df["answer_mode"].tolist() == ["Legal"]
    assert df["rating"].tolist() == ["useful"]
    assert df["written_feedback"].fillna("").tolist() == [""]
    assert df["source"].tolist() == ["chatbot_feedback"]
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
        answer_mode="Student",
        feedback_path=feedback_path,
    )

    df = pd.read_csv(feedback_path)
    assert df.columns.tolist() == [
        "timestamp",
        "user_id",
        "name",
        "role",
        "query",
        "answer_mode",
        "rating",
        "written_feedback",
        "source",
    ]
    assert df["user_id"].tolist() == ["user-3"]
    assert df["role"].tolist() == ["Researcher"]
    assert df["answer_mode"].tolist() == ["Student"]
    assert df["rating"].tolist() == ["not_useful"]

    shutil.rmtree(test_root)


def test_save_feedback_appends_written_feedback_to_csv():
    test_root = Path("test_artifacts") / "ui_tracking"
    if test_root.exists():
        shutil.rmtree(test_root)

    feedback_path = test_root / "feedback.csv"

    save_feedback(
        "benefit of doubt",
        "useful",
        user_id="user-4",
        name="Asha",
        role="Law Student",
        answer_mode="Student",
        written_feedback="The takeaway helped, sources were clear.",
        feedback_path=feedback_path,
    )

    df = pd.read_csv(feedback_path)
    assert df["answer_mode"].tolist() == ["Student"]
    assert df["rating"].tolist() == ["useful"]
    assert df["written_feedback"].tolist() == ["The takeaway helped, sources were clear."]
    assert df["source"].tolist() == ["chatbot_feedback"]

    shutil.rmtree(test_root)


def test_save_feedback_shows_debug_error_only_when_enabled(monkeypatch):
    calls = []

    def failing_save_feedback_to_sheets(**kwargs):
        raise RuntimeError("Missing Streamlit secret: GOOGLE_SHEET_ID")

    monkeypatch.setattr("src.utils.gsheets_logger.save_feedback", failing_save_feedback_to_sheets)
    monkeypatch.setattr("src.ui.app.is_gsheets_debug_enabled", lambda: True)
    monkeypatch.setattr("src.ui.app.st.error", lambda message: calls.append(("error", message)))
    monkeypatch.setattr("src.ui.app.st.exception", lambda exc: calls.append(("exception", str(exc))))

    assert save_feedback("query", "useful", user_id="user-1", role="Law Student") is False
    assert calls[0][0] == "error"
    assert "GOOGLE_SHEET_ID" in calls[0][1]
    assert calls[1] == ("exception", "Missing Streamlit secret: GOOGLE_SHEET_ID")


def test_save_feedback_hides_debug_error_when_disabled(monkeypatch):
    calls = []

    def failing_save_feedback_to_sheets(**kwargs):
        raise RuntimeError("Missing Streamlit secret: GOOGLE_SHEET_ID")

    monkeypatch.setattr("src.utils.gsheets_logger.save_feedback", failing_save_feedback_to_sheets)
    monkeypatch.setattr("src.ui.app.is_gsheets_debug_enabled", lambda: False)
    monkeypatch.setattr("src.ui.app.st.error", lambda message: calls.append(("error", message)))
    monkeypatch.setattr("src.ui.app.st.exception", lambda exc: calls.append(("exception", str(exc))))

    assert save_feedback("query", "useful", user_id="user-1", role="Law Student") is False
    assert calls == []


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

    log_query("query one", "user-1", "Asha", "Law Student", "asha@example.com", "Legal", query_log_path=query_log_path)
    log_query("query two", "user-2", "", "Researcher", "", "Student", query_log_path=query_log_path)
    query_df = pd.read_csv(query_log_path, keep_default_na=False)
    assert query_df["role"].tolist() == ["Law Student", "Researcher"]
    assert query_df["answer_mode"].tolist() == ["Legal", "Student"]
    assert query_df["source"].tolist() == ["chatbot_query", "chatbot_query"]
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


def test_build_impact_stats_uses_live_counts_when_available():
    stats = {
        "total_queries": 125,
        "unique_users": 14,
        "total_feedback": 10,
        "useful_feedback_percent": 80.0,
        "not_useful_feedback_percent": 20.0,
    }

    impact = build_impact_stats(stats)

    assert impact[0] == ("Legal Queries Processed", "125+")
    assert impact[1] == ("Helpful Responses", "80%")
    assert impact[2] == ("Active Testers", "14")
    assert impact[3] == ("Grounding", "Real judgments")


def test_build_impact_stats_uses_demo_safe_fallbacks_for_empty_counts():
    stats = {
        "total_queries": 0,
        "unique_users": 0,
        "total_feedback": 0,
        "useful_feedback_percent": 0.0,
        "not_useful_feedback_percent": 0.0,
    }

    impact = build_impact_stats(stats)

    assert impact[0][1].endswith("+")
    assert impact[1][1].endswith("%")
    assert impact[2][1] == "Active law student testing"


def test_get_user_facing_error_message_hides_provider_details():
    assert "high demand" in get_user_facing_error_message(Exception("429 rate limit")).lower()
    assert "connection issue" in get_user_facing_error_message(Exception("Connection timeout")).lower()
    assert "legal precedent" in get_user_facing_error_message(Exception("Vectorstore not found")).lower()
