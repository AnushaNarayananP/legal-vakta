"""Google Sheets logging for Legal Vakta MVP usage tracking."""

import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SERVICE_ACCOUNT_FILE = PROJECT_ROOT / "service_account.json"

SHEET_NAME = "Legal_Vakta_Logs"
QUERIES_WORKSHEET = "queries"
FEEDBACK_WORKSHEET = "feedback"
QUERY_HEADERS = ["timestamp", "user_id", "name", "role", "query"]
FEEDBACK_HEADERS = ["timestamp", "user_id", "name", "role", "query", "feedback"]
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
            return None
        service_account_info = dict(st.secrets["gcp_service_account"])
        if not service_account_info:
            raise ValueError("st.secrets['gcp_service_account'] is empty.")
        return service_account_info
    except Exception:
        return None


def _get_credential_file_path() -> Path:
    """Return configured service account file path, defaulting to project root."""
    credential_path = (
        os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE")
        or os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    )
    return Path(credential_path) if credential_path else DEFAULT_SERVICE_ACCOUNT_FILE


def get_service_account_email() -> str:
    """Return service account email for sheet-sharing diagnostics."""
    path = _get_credential_file_path()
    if path.exists():
        from google.oauth2.service_account import Credentials

        credentials = Credentials.from_service_account_file(path, scopes=SCOPES)
        return credentials.service_account_email

    streamlit_info = _load_streamlit_service_account_info()
    if streamlit_info:
        return streamlit_info.get("client_email", "")

    return ""


def get_gspread_client():
    """Create an authenticated gspread client."""
    import gspread
    from google.oauth2.service_account import Credentials

    path = _get_credential_file_path()

    if path.exists():
        credentials = Credentials.from_service_account_file(path, scopes=SCOPES)
    elif streamlit_info := _load_streamlit_service_account_info():
        credentials = Credentials.from_service_account_info(streamlit_info, scopes=SCOPES)
    else:
        raise FileNotFoundError(
            "Google service account credentials not found. Configure Streamlit "
            "secrets [gcp_service_account] or place service_account.json in the "
            "project root. You can also set GOOGLE_SERVICE_ACCOUNT_FILE to a JSON key file."
        )

    return gspread.authorize(credentials)


def get_spreadsheet(client=None):
    """Open the existing spreadsheet by ID or name without creating Drive files."""
    gspread_client = client or get_gspread_client()
    sheet_id = os.getenv("GOOGLE_SHEET_ID", "").strip().strip('"')
    try:
        if sheet_id:
            return gspread_client.open_by_key(sheet_id)
        return gspread_client.open(SHEET_NAME)
    except Exception as exc:
        raise RuntimeError(
            f"Could not open existing Google Sheet '{SHEET_NAME}'. "
            "Do not create a new sheet from the app. Confirm the sheet exists, "
            "GOOGLE_SHEET_ID is correct, and it is shared with the service account. "
            f"Original error: {exc}"
        ) from exc


def format_google_sheets_error(exc: Exception) -> str:
    """Return a clear user-facing Google Sheets error message."""
    error_text = str(exc)
    normalized = error_text.lower()

    if "quota" in normalized or "storage quota" in normalized:
        return (
            "Google Drive storage quota exceeded. The app will not create a new "
            "spreadsheet or worksheet. Open the existing Legal_Vakta_Logs sheet, "
            "confirm GOOGLE_SHEET_ID is correct, and free Drive storage if needed."
        )
    if "worksheet" in normalized or "queries and feedback" in normalized:
        return MISSING_WORKSHEETS_MESSAGE
    if "403" in normalized or "permission" in normalized or "shared" in normalized:
        return (
            "Google Sheet access failed. Share Legal_Vakta_Logs with the service "
            "account email using Editor access."
        )
    if "not found" in normalized or "could not open" in normalized:
        return (
            "Could not open the existing Google Sheet Legal_Vakta_Logs. Confirm "
            "the sheet exists and GOOGLE_SHEET_ID points to it."
        )
    return error_text


def get_or_create_worksheet(spreadsheet, title: str, headers: List[str]):
    """Return an existing worksheet and verify headers without creating worksheets."""
    try:
        worksheet = spreadsheet.worksheet(title)
    except Exception as exc:
        raise RuntimeError(MISSING_WORKSHEETS_MESSAGE) from exc

    existing_values = worksheet.get_all_values()
    if not existing_values:
        raise RuntimeError(
            f"Worksheet '{title}' is empty. Add this header row manually: "
            f"{','.join(headers)}"
        )
    if existing_values[0][: len(headers)] != headers:
        raise RuntimeError(
            f"Worksheet '{title}' has incorrect headers. Expected: "
            f"{','.join(headers)}"
        )
    return worksheet


def append_record(worksheet_name: str, headers: List[str], row: Dict, spreadsheet=None):
    """Append one record to a worksheet."""
    active_spreadsheet = spreadsheet or get_spreadsheet()
    worksheet = get_or_create_worksheet(active_spreadsheet, worksheet_name, headers)
    worksheet.append_row([row.get(header, "") for header in headers])


def get_records(worksheet_name: str, headers: List[str], spreadsheet=None) -> List[Dict]:
    """Read worksheet records."""
    active_spreadsheet = spreadsheet or get_spreadsheet()
    worksheet = get_or_create_worksheet(active_spreadsheet, worksheet_name, headers)
    return worksheet.get_all_records()


def log_query(user_id: str, name: str, role: str, query: str, spreadsheet=None):
    """Log one user query to the queries worksheet."""
    append_record(
        QUERIES_WORKSHEET,
        QUERY_HEADERS,
        {
            "timestamp": current_timestamp(),
            "user_id": user_id,
            "name": name,
            "role": role,
            "query": query,
        },
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
