from src.utils.gsheets_logger import (
    FEEDBACK_HEADERS,
    QUERY_HEADERS,
    WAITLIST_HEADERS,
    append_query_log,
    calculate_usage_stats,
    log_query,
    save_feedback,
    save_waitlist_lead,
)


class FakeWorksheet:
    def __init__(self, values=None):
        self.values = values or []
        self.appended_rows = []
        self.value_input_options = []
        self.updated_ranges = []

    def get_all_values(self):
        return self.values

    def get_all_records(self):
        if not self.values:
            return []
        headers = self.values[0]
        return [dict(zip(headers, row)) for row in self.values[1:]]

    def update(self, range_name=None, values=None):
        self.updated_ranges.append((range_name, values))
        if range_name in (None, "A1:F1", "A1:G1", "A1:H1", "A1:I1"):
            self.values = values
        elif range_name and range_name.startswith("A") and values:
            row_number = int(range_name.split(":")[0][1:])
            while len(self.values) < row_number:
                self.values.append([])
            self.values[row_number - 1] = values[0]

    def append_row(self, row, value_input_option=None):
        self.appended_rows.append(row)
        self.value_input_options.append(value_input_option)


class FakeSpreadsheet:
    def __init__(self, worksheets=None):
        self.worksheets = worksheets or {}

    def worksheet(self, title):
        if title not in self.worksheets:
            raise RuntimeError("missing worksheet")
        return self.worksheets[title]

    def add_worksheet(self, title, rows, cols):
        worksheet = FakeWorksheet()
        self.worksheets[title] = worksheet
        return worksheet


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


def test_calculate_usage_stats_uses_rating_column_when_available():
    query_records = [{"user_id": "u1", "query": "q1"}]
    feedback_records = [
        {"user_id": "u1", "rating": "useful", "written_feedback": "Good"},
        {"user_id": "u2", "rating": "not_useful", "written_feedback": "Confusing"},
    ]

    assert calculate_usage_stats(query_records, feedback_records) == {
        "total_queries": 1,
        "unique_users": 1,
        "total_feedback": 2,
        "useful_feedback_percent": 50.0,
        "not_useful_feedback_percent": 50.0,
    }


def test_sheet_headers_match_tracking_contract():
    assert QUERY_HEADERS == [
        "timestamp",
        "user_id",
        "query",
        "role",
        "answer_mode",
        "confidence",
        "source",
    ]
    assert FEEDBACK_HEADERS == [
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
    assert WAITLIST_HEADERS == ["timestamp", "user_id", "name", "email", "role", "source"]


def test_save_feedback_appends_rating_written_feedback_and_source():
    feedback = FakeWorksheet(values=[FEEDBACK_HEADERS])
    spreadsheet = FakeSpreadsheet({"feedback": feedback})

    save_feedback(
        user_id="user-1",
        name="Asha",
        role="Law Student",
        query="bail",
        answer_mode="Student",
        rating="useful",
        written_feedback="Clear answer",
        spreadsheet=spreadsheet,
    )

    assert len(feedback.appended_rows) == 1
    assert len(feedback.appended_rows[0]) == len(FEEDBACK_HEADERS)
    assert feedback.appended_rows[0][1:] == [
        "user-1",
        "Asha",
        "Law Student",
        "bail",
        "Student",
        "useful",
        "Clear answer",
        "chatbot_feedback",
    ]


def test_save_feedback_updates_legacy_feedback_headers_before_appending():
    legacy_headers = ["timestamp", "user_id", "name", "role", "query", "feedback"]
    feedback = FakeWorksheet(values=[legacy_headers])
    spreadsheet = FakeSpreadsheet({"feedback": feedback})

    save_feedback(
        user_id="user-2",
        name="",
        role="Researcher",
        query="evidence",
        answer_mode="Legal",
        rating="not_useful",
        written_feedback="Needed more sources",
        spreadsheet=spreadsheet,
    )

    assert feedback.values == [FEEDBACK_HEADERS]
    assert feedback.appended_rows[0][1:] == [
        "user-2",
        "",
        "Researcher",
        "evidence",
        "Legal",
        "not_useful",
        "Needed more sources",
        "chatbot_feedback",
    ]


def test_save_feedback_updates_current_feedback_headers_before_appending_answer_mode():
    current_headers = [
        "timestamp",
        "user_id",
        "name",
        "role",
        "query",
        "rating",
        "written_feedback",
        "source",
    ]
    feedback = FakeWorksheet(values=[current_headers])
    spreadsheet = FakeSpreadsheet({"feedback": feedback})

    save_feedback(
        user_id="user-3",
        name="Asha",
        role="Law Student",
        query="benefit of doubt",
        answer_mode="Student",
        rating="useful",
        written_feedback="Would come back",
        spreadsheet=spreadsheet,
    )

    assert feedback.values == [FEEDBACK_HEADERS]
    assert feedback.appended_rows[0][1:] == [
        "user-3",
        "Asha",
        "Law Student",
        "benefit of doubt",
        "Student",
        "useful",
        "Would come back",
        "chatbot_feedback",
    ]


def test_append_query_log_writes_clean_query_analytics_row():
    queries = FakeWorksheet(values=[QUERY_HEADERS])
    spreadsheet = FakeSpreadsheet({"queries": queries})

    append_query_log(
        user_id="user-1",
        query="benefit of doubt",
        role="Law Student",
        answer_mode="Legal",
        confidence="High",
        source="chatbot_query",
        spreadsheet=spreadsheet,
    )

    assert len(queries.appended_rows) == 1
    assert len(queries.appended_rows[0]) == len(QUERY_HEADERS)
    assert queries.appended_rows[0][1:] == [
        "user-1",
        "benefit of doubt",
        "Law Student",
        "Legal",
        "High",
        "chatbot_query",
    ]
    assert queries.value_input_options == ["USER_ENTERED"]


def test_append_query_log_defaults_to_na_confidence_and_preserves_source():
    queries = FakeWorksheet(values=[QUERY_HEADERS])
    spreadsheet = FakeSpreadsheet({"queries": queries})

    append_query_log(
        user_id="user-1",
        query="benefit of doubt",
        role="Law Student",
        answer_mode="Student",
        confidence="Unexpected",
        source="manual_override",
        spreadsheet=spreadsheet,
    )

    assert queries.appended_rows[0][1:] == [
        "user-1",
        "benefit of doubt",
        "Law Student",
        "Student",
        "N/A",
        "manual_override",
    ]


def test_backward_compatible_log_query_preserves_source():
    queries = FakeWorksheet(values=[QUERY_HEADERS])
    spreadsheet = FakeSpreadsheet({"queries": queries})

    log_query(
        user_id="user-1",
        role="Law Student",
        query="benefit of doubt",
        answer_mode="Student",
        source="suggested_query",
        spreadsheet=spreadsheet,
    )

    assert queries.appended_rows[0][1:] == [
        "user-1",
        "benefit of doubt",
        "Law Student",
        "Student",
        "N/A",
        "suggested_query",
    ]


def test_append_query_log_updates_legacy_query_headers_before_appending():
    legacy_headers = ["timestamp", "user_id", "name", "email", "role", "query"]
    queries = FakeWorksheet(values=[legacy_headers])
    spreadsheet = FakeSpreadsheet({"queries": queries})

    append_query_log(
        user_id="user-2",
        query="bail",
        role="Lawyer",
        answer_mode="Legal",
        confidence="Medium",
        spreadsheet=spreadsheet,
    )

    assert queries.values == [QUERY_HEADERS]
    assert queries.appended_rows[0][1:] == [
        "user-2",
        "bail",
        "Lawyer",
        "Legal",
        "Medium",
        "chatbot_query",
    ]


def test_append_query_log_adds_answer_mode_to_old_clean_query_headers():
    old_clean_headers = ["timestamp", "user_id", "query", "role", "confidence", "source"]
    queries = FakeWorksheet(values=[old_clean_headers])
    spreadsheet = FakeSpreadsheet({"queries": queries})

    append_query_log(
        user_id="user-3",
        query="circumstantial evidence",
        role="Researcher",
        answer_mode="Student",
        confidence="Low",
        spreadsheet=spreadsheet,
    )

    assert queries.values == [QUERY_HEADERS]
    assert queries.appended_rows[0][1:] == [
        "user-3",
        "circumstantial evidence",
        "Researcher",
        "Student",
        "Low",
        "chatbot_query",
    ]


def test_save_waitlist_lead_appends_landing_source_to_existing_sheet():
    waitlist = FakeWorksheet(values=[WAITLIST_HEADERS])
    spreadsheet = FakeSpreadsheet({"waitlist": waitlist})

    result = save_waitlist_lead("user-1", "Asha", "asha@example.com", "Law Student", spreadsheet)

    assert result == "created"
    assert len(waitlist.appended_rows) == 1
    assert waitlist.appended_rows[0][1:] == [
        "user-1",
        "Asha",
        "asha@example.com",
        "Law Student",
        "waitlist_form",
    ]


def test_save_waitlist_lead_creates_missing_waitlist_sheet_when_allowed():
    spreadsheet = FakeSpreadsheet()

    result = save_waitlist_lead("user-2", "", "lead@example.com", "Researcher", spreadsheet)

    assert result == "created"
    waitlist = spreadsheet.worksheets["waitlist"]
    assert waitlist.values == [WAITLIST_HEADERS]
    assert waitlist.appended_rows[0][5] == "waitlist_form"


def test_save_waitlist_lead_does_not_duplicate_existing_email_when_unchanged():
    waitlist = FakeWorksheet(
        values=[
            WAITLIST_HEADERS,
            ["old-time", "user-1", "Asha", "asha@example.com", "Law Student", "waitlist_form"],
        ]
    )
    spreadsheet = FakeSpreadsheet({"waitlist": waitlist})

    result = save_waitlist_lead("user-2", "Asha", "ASHA@example.com", "Law Student", spreadsheet)

    assert result == "existing"
    assert waitlist.appended_rows == []
    assert waitlist.updated_ranges == []


def test_save_waitlist_lead_updates_name_and_role_for_existing_email_without_duplicate():
    waitlist = FakeWorksheet(
        values=[
            WAITLIST_HEADERS,
            ["old-time", "user-1", "Asha", "asha@example.com", "Law Student", "waitlist_form"],
        ]
    )
    spreadsheet = FakeSpreadsheet({"waitlist": waitlist})

    result = save_waitlist_lead("user-2", "Asha N.", "asha@example.com", "Lawyer", spreadsheet)

    assert result == "updated"
    assert waitlist.appended_rows == []
    assert waitlist.values[1] == [
        "old-time",
        "user-1",
        "Asha N.",
        "asha@example.com",
        "Lawyer",
        "waitlist_form",
    ]


def test_save_waitlist_lead_rejects_invalid_email():
    spreadsheet = FakeSpreadsheet({"waitlist": FakeWorksheet(values=[WAITLIST_HEADERS])})

    try:
        save_waitlist_lead("user-3", "No Email", "invalid-email", "Other", spreadsheet)
    except ValueError as exc:
        assert "valid email" in str(exc)
    else:
        raise AssertionError("Expected invalid email to raise ValueError")
