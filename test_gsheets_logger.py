from src.utils.gsheets_logger import (
    FEEDBACK_HEADERS,
    QUERY_HEADERS,
    WAITLIST_HEADERS,
    calculate_usage_stats,
    save_waitlist_lead,
)


class FakeWorksheet:
    def __init__(self, values=None):
        self.values = values or []
        self.appended_rows = []

    def get_all_values(self):
        return self.values

    def update(self, range_name=None, values=None):
        self.values = values

    def append_row(self, row):
        self.appended_rows.append(row)


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


def test_sheet_headers_match_tracking_contract():
    assert QUERY_HEADERS == ["timestamp", "user_id", "name", "email", "role", "query"]
    assert FEEDBACK_HEADERS == [
        "timestamp",
        "user_id",
        "name",
        "role",
        "query",
        "feedback",
    ]
    assert WAITLIST_HEADERS == ["timestamp", "user_id", "name", "email", "role", "source"]


def test_save_waitlist_lead_appends_landing_source_to_existing_sheet():
    waitlist = FakeWorksheet(values=[WAITLIST_HEADERS])
    spreadsheet = FakeSpreadsheet({"waitlist": waitlist})

    save_waitlist_lead("user-1", "Asha", "asha@example.com", "Law Student", spreadsheet)

    assert len(waitlist.appended_rows) == 1
    assert waitlist.appended_rows[0][1:] == [
        "user-1",
        "Asha",
        "asha@example.com",
        "Law Student",
        "landing_page",
    ]


def test_save_waitlist_lead_creates_missing_waitlist_sheet_when_allowed():
    spreadsheet = FakeSpreadsheet()

    save_waitlist_lead("user-2", "", "lead@example.com", "Researcher", spreadsheet)

    waitlist = spreadsheet.worksheets["waitlist"]
    assert waitlist.values == [WAITLIST_HEADERS]
    assert waitlist.appended_rows[0][5] == "landing_page"


def test_save_waitlist_lead_rejects_invalid_email():
    spreadsheet = FakeSpreadsheet({"waitlist": FakeWorksheet(values=[WAITLIST_HEADERS])})

    try:
        save_waitlist_lead("user-3", "No Email", "invalid-email", "Other", spreadsheet)
    except ValueError as exc:
        assert "valid email" in str(exc)
    else:
        raise AssertionError("Expected invalid email to raise ValueError")
