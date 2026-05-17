"""Google Sheets logging for SpaceL AI MVP usage tracking."""

from datetime import datetime
from typing import Dict, List, Optional

import pandas as pd

SHEET_NAME = "Legal_Vakta_Logs"
QUERIES_WORKSHEET = "queries"
FEEDBACK_WORKSHEET = "feedback"
WAITLIST_WORKSHEET = "waitlist"
QUERY_HEADERS = ["timestamp", "user_id", "query", "role", "confidence", "source"]
LEGACY_QUERY_HEADERS = ["timestamp", "user_id", "name", "email", "role", "query"]
FEEDBACK_HEADERS = ["timestamp", "user_id", "name", "role", "query", "feedback"]
WAITLIST_HEADERS = ["timestamp", "user_id", "name", "email", "role", "source"]
MISSING_WORKSHEETS_MESSAGE = "Please create worksheets named queries and feedback manually."
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


def current_timestamp():
    """Return an ISO timestamp for usage analytics."""
    return datetime.now().isoformat(timespec="seconds")


def _load_streamlit_service_account_info() -> Optional[Dict]:
    """Load service account info from Streamlit secrets when available."""
    try:
        import streamlit as st

        if "gcp_service_account" not in st.secrets:
            raise RuntimeError(
                "Missing Streamlit secret: gcp_service_account. Add your Google "
                "service account fields under [gcp_service_account] in Streamlit secrets."
            )
        service_account_info = dict(st.secrets["gcp_service_account"])
        if not service_account_info:
            raise ValueError("st.secrets['gcp_service_account'] is empty.")
        return service_account_info
    except Exception as exc:
        raise RuntimeError(f"Google service account secrets are not configured: {exc}") from exc


def get_service_account_email() -> str:
    """Return service account email for sheet-sharing diagnostics."""
    return _load_streamlit_service_account_info().get("client_email", "")


def get_gspread_client():
    """Create an authenticated gspread client from Streamlit Cloud secrets."""
    import gspread
    from google.oauth2.service_account import Credentials

    service_account_info = _load_streamlit_service_account_info()
    credentials = Credentials.from_service_account_info(
        service_account_info,
        scopes=SCOPES,
    )

    return gspread.authorize(credentials)


def get_spreadsheet(client=None):
    """Open the existing spreadsheet by Streamlit secret ID without creating Drive files."""
    import streamlit as st

    gspread_client = client or get_gspread_client()
    sheet_id = str(st.secrets.get("GOOGLE_SHEET_ID", "")).strip()
    if not sheet_id:
        raise RuntimeError(
            "Missing Streamlit secret: GOOGLE_SHEET_ID. Add your Google Sheet ID "
            "to Streamlit secrets."
        )

    try:
        return gspread_client.open_by_key(sheet_id)
    except Exception as exc:
        raise RuntimeError(
            f"Could not open existing Google Sheet '{SHEET_NAME}'. "
            "Do not create a new sheet from the app. Confirm GOOGLE_SHEET_ID is "
            "correct and the sheet is shared with the service account. "
            f"Original error: {exc}"
        ) from exc


def format_google_sheets_error(exc: Exception) -> str:
    """Return a clear user-facing Google Sheets error message."""
    error_text = str(exc)
    normalized = error_text.lower()

    if "quota" in normalized or "storage quota" in normalized:
        return (
            "Google Drive storage quota exceeded. The app will not create a new "
            "spreadsheet or worksheet. Open the existing SpaceL AI analytics sheet, "
            "confirm GOOGLE_SHEET_ID is correct, and free Drive storage if needed."
        )
    if "worksheet" in normalized or "queries and feedback" in normalized:
        return MISSING_WORKSHEETS_MESSAGE
    if "403" in normalized or "permission" in normalized or "shared" in normalized:
        return (
            "Google Sheet access failed. Share the SpaceL AI analytics sheet with the service "
            "account email using Editor access."
        )
    if "not found" in normalized or "could not open" in normalized:
        return (
            "Could not open the existing SpaceL AI analytics sheet. Confirm "
            "the sheet exists and GOOGLE_SHEET_ID points to it."
        )
    return error_text


def ensure_worksheet(spreadsheet, title: str, headers: List[str], create_missing: bool = False):
    """Return a worksheet with the expected headers, creating/updating where safe."""
    try:
        worksheet = spreadsheet.worksheet(title)
    except Exception as exc:
        if not create_missing:
            raise RuntimeError(MISSING_WORKSHEETS_MESSAGE) from exc
        worksheet = spreadsheet.add_worksheet(title=title, rows=1, cols=len(headers))
        worksheet.update(range_name=f"A1:{chr(64 + len(headers))}1", values=[headers])
        return worksheet

    existing_values = worksheet.get_all_values()
    if not existing_values:
        worksheet.update(range_name=f"A1:{chr(64 + len(headers))}1", values=[headers])
        return worksheet

    # The queries sheet used to contain profile columns. Update only the header row
    # so future appended query analytics use the clean MVP schema and column count.
    if title == QUERIES_WORKSHEET and existing_values[0][: len(LEGACY_QUERY_HEADERS)] == LEGACY_QUERY_HEADERS:
        worksheet.update(range_name="A1:F1", values=[headers])
        return worksheet

    if existing_values[0][: len(headers)] != headers:
        raise RuntimeError(
            f"Worksheet '{title}' has incorrect headers. Expected: "
            f"{','.join(headers)}"
        )
    return worksheet


def get_or_create_worksheet(spreadsheet, title: str, headers: List[str]):
    """Return an existing worksheet and verify or initialize its headers."""
    return ensure_worksheet(spreadsheet, title, headers, create_missing=False)


def get_or_create_waitlist_worksheet(spreadsheet):
    """Return the waitlist worksheet, creating it when Google Sheets allows it."""
    try:
        worksheet = spreadsheet.worksheet(WAITLIST_WORKSHEET)
    except Exception as exc:
        try:
            worksheet = spreadsheet.add_worksheet(
                title=WAITLIST_WORKSHEET,
                rows=1,
                cols=len(WAITLIST_HEADERS),
            )
            worksheet.update(range_name="A1:F1", values=[WAITLIST_HEADERS])
            return worksheet
        except Exception as create_exc:
            raise RuntimeError(
                "Worksheet 'waitlist' is missing. Please create it manually with "
                "headers: timestamp,user_id,name,email,role,source"
            ) from create_exc

    existing_values = worksheet.get_all_values()
    if not existing_values:
        try:
            worksheet.update(range_name="A1:F1", values=[WAITLIST_HEADERS])
        except Exception as exc:
            raise RuntimeError(
                "Worksheet 'waitlist' is empty. Add this header row manually: "
                "timestamp,user_id,name,email,role,source"
            ) from exc
    elif existing_values[0][: len(WAITLIST_HEADERS)] != WAITLIST_HEADERS:
        raise RuntimeError(
            "Worksheet 'waitlist' has incorrect headers. Expected: "
            "timestamp,user_id,name,email,role,source"
        )
    return worksheet


def append_record(worksheet_name: str, headers: List[str], row: Dict, spreadsheet=None):
    """Append one record to a worksheet."""
    active_spreadsheet = spreadsheet or get_spreadsheet()
    worksheet = ensure_worksheet(active_spreadsheet, worksheet_name, headers)
    worksheet.append_row([row.get(header, "") for header in headers])


def get_records(worksheet_name: str, headers: List[str], spreadsheet=None) -> List[Dict]:
    """Read worksheet records."""
    active_spreadsheet = spreadsheet or get_spreadsheet()
    worksheet = get_or_create_worksheet(active_spreadsheet, worksheet_name, headers)
    return worksheet.get_all_records()


def normalize_query_confidence(confidence: str) -> str:
    """Keep query analytics confidence values within the approved sheet labels."""
    if confidence in {"High", "Medium", "Low"}:
        return confidence
    return "N/A"


def build_query_log_row(user_id: str, query: str, role: str, confidence: str, source: str):
    """Build a query row in the exact queries sheet column order A-F."""
    return [
        current_timestamp(),
        user_id,
        query,
        role,
        normalize_query_confidence(confidence),
        source,
    ]


def append_query_log(
    user_id: str,
    query: str,
    role: str,
    confidence: str = "N/A",
    source: str = "chatbot_query",
    spreadsheet=None,
):
    """Append one clean query analytics row without profile details."""
    active_spreadsheet = spreadsheet or get_spreadsheet()
    worksheet = ensure_worksheet(active_spreadsheet, QUERIES_WORKSHEET, QUERY_HEADERS)

    # Column mapping is intentionally explicit to prevent old profile fields from
    # shifting query, role, confidence, or source into the wrong Google Sheet cells.
    row = build_query_log_row(
        user_id=user_id,
        query=query,
        role=role,
        confidence=confidence,
        source=source,
    )
    worksheet.append_row(row, value_input_option="USER_ENTERED")


def log_query(
    user_id: str,
    name: str = "",
    email: str = "",
    role: str = "",
    query: str = "",
    source: str = "chatbot_query",
    spreadsheet=None,
):
    """Backward-compatible wrapper for clean query analytics logging."""
    append_query_log(
        user_id=user_id,
        query=query,
        role=role,
        confidence="N/A",
        source=source,
        spreadsheet=spreadsheet,
    )


def save_feedback(
    user_id: str,
    name: str,
    role: str,
    query: str,
    feedback: str,
    spreadsheet=None,
):
    """Log one feedback event to the feedback worksheet."""
    append_record(
        FEEDBACK_WORKSHEET,
        FEEDBACK_HEADERS,
        {
            "timestamp": current_timestamp(),
            "user_id": user_id,
            "name": name,
            "role": role,
            "query": query,
            "feedback": feedback,
        },
        spreadsheet=spreadsheet,
    )


def save_waitlist_lead(
    user_id: str,
    name: str,
    email: str,
    role: str,
    spreadsheet=None,
):
    """Create or update one waitlist lead, keyed by email."""
    if not email or "@" not in email:
        raise ValueError("A valid email address is required.")

    clean_name = name.strip() if name else ""
    clean_email = email.strip()
    clean_role = role.strip() if role else ""
    active_spreadsheet = spreadsheet or get_spreadsheet()
    worksheet = get_or_create_waitlist_worksheet(active_spreadsheet)

    email_key = clean_email.lower()
    records = worksheet.get_all_records()
    for index, record in enumerate(records, start=2):
        existing_email = str(record.get("email", "")).strip()
        if existing_email.lower() != email_key:
            continue

        existing_name = str(record.get("name", "")).strip()
        existing_role = str(record.get("role", "")).strip()
        if existing_name == clean_name and existing_role == clean_role:
            return "existing"

        updated_row = [
            str(record.get("timestamp", "")).strip() or current_timestamp(),
            str(record.get("user_id", "")).strip() or user_id,
            clean_name,
            existing_email,
            clean_role,
            str(record.get("source", "")).strip() or "waitlist_form",
        ]
        worksheet.update(range_name=f"A{index}:F{index}", values=[updated_row])
        return "updated"

    worksheet.append_row(
        [
            current_timestamp(),
            user_id,
            clean_name,
            clean_email,
            clean_role,
            "waitlist_form",
        ]
    )
    return "created"


def calculate_usage_stats(query_records: List[Dict], feedback_records: List[Dict]):
    """Calculate MVP usage metrics from worksheet records."""
    query_df = pd.DataFrame(query_records)
    feedback_df = pd.DataFrame(feedback_records)
    total_feedback = len(feedback_df)

    useful_percent = 0.0
    not_useful_percent = 0.0
    if total_feedback and "feedback" in feedback_df.columns:
        useful_percent = round(
            ((feedback_df["feedback"] == "useful").sum() / total_feedback) * 100,
            1,
        )
        not_useful_percent = round(
            ((feedback_df["feedback"] == "not_useful").sum() / total_feedback) * 100,
            1,
        )

    unique_users = 0
    if not query_df.empty and "user_id" in query_df.columns:
        unique_users = int(query_df["user_id"].nunique())

    return {
        "total_queries": len(query_df),
        "unique_users": unique_users,
        "total_feedback": total_feedback,
        "useful_feedback_percent": useful_percent,
        "not_useful_feedback_percent": not_useful_percent,
    }


def load_usage_stats(spreadsheet=None):
    """Load usage stats from Google Sheets, safely handling empty sheets."""
    query_records = get_records(QUERIES_WORKSHEET, QUERY_HEADERS, spreadsheet=spreadsheet)
    feedback_records = get_records(
        FEEDBACK_WORKSHEET,
        FEEDBACK_HEADERS,
        spreadsheet=spreadsheet,
    )
    return calculate_usage_stats(query_records, feedback_records)
