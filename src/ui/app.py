"""Streamlit UI for SpaceL AI."""

import csv
import hashlib
import inspect
import sys
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import Settings
from src.ui.formatting import (
    SECTION_ICONS,
    SECTION_TITLES,
    STUDENT_SECTION_TITLES,
    build_key_insight,
    clean_snippet,
    format_case_label,
    get_source_display_metadata,
    parse_structured_answer,
    sort_source_evidence,
)
from src.ui.source_evidence_ui import render_source_evidence_section


PROCESSED_DATA_DIR = PROJECT_ROOT / "data" / "processed"
QUERY_LOG_PATH = PROCESSED_DATA_DIR / "query_logs.csv"
FEEDBACK_PATH = PROCESSED_DATA_DIR / "feedback.csv"
PRODUCT_NAME = "SpaceL AI"
PRODUCT_TAGLINE = "AI legal research in seconds, grounded in real court judgments."
SUGGESTED_QUERIES = [
    "Benefit of doubt in criminal appeals",
    "Bail conditions in serious offences",
    "Circumstantial evidence cases",
]
SUGGESTED_QUERY_LABELS = [
    "Benefit of doubt",
    "Bail conditions",
    "Circumstantial evidence",
]
ROLE_OPTIONS = ["Law Student", "Lawyer", "Researcher", "Other"]
ANSWER_MODE_OPTIONS = ["Legal", "Student"]
LEGAL_DISCLAIMER_TEXT = (
    "&#9888;&#65039; Disclaimer: SpaceL AI provides AI-assisted legal research "
    "and not legal advice. Please independently verify citations and consult a qualified advocate."
)
LOCAL_STORAGE_USER_ID_KEY = "spacel_user_id"
LOCAL_STORAGE_UNSET = object()
QUERY_SOURCE_CHATBOT = "chatbot_query"
QUERY_SOURCE_SUGGESTED = "suggested_query"
QUERY_SOURCE_MODE_REGENERATION = "mode_regeneration"
QUERY_SOURCE_MANUAL_TEST = "manual_test"
PENDING_QUERY_KEY = "pending_query"
PENDING_QUERY_SOURCE_KEY = "pending_query_source"
EMPTY_USAGE_STATS = {
    "total_queries": 0,
    "unique_users": 0,
    "total_feedback": 0,
    "useful_feedback_percent": 0.0,
    "not_useful_feedback_percent": 0.0,
}


st.set_page_config(
    page_title=PRODUCT_NAME,
    page_icon="SL",
    layout="wide",
)


st.markdown(
    """
    <style>
    :root {
        --spacel-blue: #0f2f5f;
        --spacel-blue-soft: #eff6ff;
        --spacel-gold: #c9972b;
        --spacel-ink: #111827;
        --spacel-muted: #4b5563;
        --spacel-line: #e5e7eb;
    }
    .block-container {max-width: 1040px; padding-top: 2.25rem; padding-bottom: 7rem;}
    .legal-subtitle {color: #4b5563; margin-bottom: 1.25rem;}
    .landing-hero {
        padding: 3.25rem 0 2.25rem 0;
        border-bottom: 1px solid var(--spacel-line);
        margin-bottom: 2rem;
    }
    .landing-kicker {
        color: var(--spacel-gold);
        font-weight: 700;
        letter-spacing: .02em;
        text-transform: uppercase;
        font-size: .82rem;
        margin-bottom: .75rem;
    }
    .landing-title {
        font-size: clamp(2.6rem, 6vw, 4.8rem);
        line-height: 1.02;
        margin: 0 0 1rem 0;
        font-weight: 800;
        color: var(--spacel-blue);
    }
    .landing-tagline {
        color: var(--spacel-ink);
        font-size: 1.28rem;
        margin-bottom: .85rem;
        max-width: 760px;
    }
    .landing-copy {
        color: var(--spacel-muted);
        font-size: 1rem;
        max-width: 720px;
        margin-bottom: 1.35rem;
    }
    .landing-section {
        padding: 1.7rem 0;
        border-bottom: 1px solid #f1f5f9;
    }
    .landing-section-title {
        color: var(--spacel-blue);
        font-size: 1.35rem;
        font-weight: 760;
        margin-bottom: .45rem;
    }
    .landing-section-copy {
        color: var(--spacel-muted);
        max-width: 720px;
        margin-bottom: 1rem;
    }
    .landing-card {
        border: 1px solid var(--spacel-line);
        background: #ffffff;
        border-radius: 8px;
        padding: 1.05rem;
        min-height: 118px;
        box-shadow: 0 1px 2px rgba(15, 47, 95, .04);
    }
    .landing-card strong {
        color: var(--spacel-blue);
    }
    .landing-muted-card {
        border: 1px dashed #cbd5e1;
        background: #f8fafc;
        border-radius: 8px;
        padding: 1.25rem;
        text-align: center;
        color: #64748b;
    }
    .landing-metric {
        border: 1px solid #dbeafe;
        background: var(--spacel-blue-soft);
        border-radius: 8px;
        padding: 1rem;
        min-height: 86px;
    }
    .landing-metric strong {
        color: var(--spacel-blue);
        font-size: 1.35rem;
    }
    .use-case-pill {
        border: 1px solid #dbeafe;
        background: #f8fafc;
        border-radius: 999px;
        padding: .55rem .8rem;
        margin-bottom: .55rem;
        color: #1f2937;
    }
    .app-anchor {
        border-top: 1px solid #e5e7eb;
        margin-top: 2rem;
        padding-top: 1.5rem;
    }
    .insight-box {
        border-left: 4px solid #2563eb;
        background: #eff6ff;
        padding: 1rem 1.1rem;
        border-radius: 8px;
        margin: 1rem 0 1.25rem 0;
    }
    .answer-card {
        border: 1px solid #e5e7eb;
        background: #ffffff;
        border-radius: 8px;
        padding: 1rem 1.1rem;
        margin: .75rem 0;
    }
    .answer-card-title {
        font-weight: 700;
        color: #111827;
        margin-bottom: .45rem;
    }
    .legal-disclaimer {
        border-top: 1px solid var(--spacel-line);
        color: #64748b;
        font-size: .86rem;
        line-height: 1.55;
        margin: 1rem 0 .85rem 0;
        padding-top: .75rem;
    }
    .source-meta {
        color: #374151;
        line-height: 1.7;
        margin-bottom: .6rem;
    }
    .section-gap {margin-top: 1.25rem;}
    div[data-testid="stHorizontalBlock"]:has(button[kind="secondary"]) {
        align-items: stretch;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def ensure_parent_folder(path):
    """Create parent folder for a CSV output path."""
    Path(path).parent.mkdir(parents=True, exist_ok=True)


def append_csv_row(path, fieldnames, row):
    """Append one row to a CSV file, writing headers when needed."""
    csv_path = Path(path)
    ensure_parent_folder(csv_path)
    write_header = not csv_path.exists() or csv_path.stat().st_size == 0

    with csv_path.open("a", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        if write_header:
            writer.writeheader()
        writer.writerow(row)


def current_timestamp():
    """Return an ISO timestamp for usage analytics."""
    return datetime.now().isoformat(timespec="seconds")


def get_feedback_key(user_id, query, answer_mode):
    """Build a stable key for one user's feedback on one query/mode answer."""
    clean_user_id = normalize_user_id(user_id) or "anonymous"
    query_hash = hashlib.sha256(str(query or "").strip().encode("utf-8")).hexdigest()[:16]
    clean_mode = str(answer_mode or "Legal").strip() or "Legal"
    return f"{clean_user_id}_{query_hash}_{clean_mode}"


def get_feedback_state(state, feedback_key):
    """Return initialized feedback state for a stable feedback key."""
    states = state.setdefault("feedback_states", {})
    current = states.setdefault(
        feedback_key,
        {
            "rating": None,
            "text": "",
            "submitted": False,
        },
    )
    current.setdefault("rating", None)
    current.setdefault("text", "")
    current.setdefault("submitted", False)
    return current


def update_feedback_state(state, feedback_key, rating=None, text=None, submitted=None):
    """Update one scoped feedback state without touching other modes or queries."""
    current = get_feedback_state(state, feedback_key)
    if rating is not None:
        current["rating"] = rating
    if text is not None:
        current["text"] = text
    if submitted is not None:
        current["submitted"] = submitted
    return current


def mark_feedback_submitted(state, feedback_key):
    """Mark one query/mode feedback state as submitted."""
    return update_feedback_state(state, feedback_key, submitted=True)


def normalize_user_id(value):
    """Return a clean user ID string, or empty string when storage returned nothing."""
    if isinstance(value, list):
        value = value[0] if value else ""
    if not isinstance(value, str):
        return ""
    return value.strip()


def get_query_param_user_id(query_params=None):
    """Read the browser-confirmed user ID passed from the localStorage bridge."""
    params = query_params if query_params is not None else st.query_params
    try:
        return normalize_user_id(params.get(LOCAL_STORAGE_USER_ID_KEY, ""))
    except Exception:
        return ""


def embed_inline_html(html, **kwargs):
    """Render trusted inline HTML/JS across current and post-deprecation Streamlit."""
    st_html = getattr(st, "html", None)
    if st_html is not None:
        try:
            signature = inspect.signature(st_html)
        except (TypeError, ValueError):
            signature = None

        if signature and "unsafe_allow_javascript" in signature.parameters:
            st_html(html, width="stretch", unsafe_allow_javascript=True)
            return

    st.iframe(html, **kwargs)


def render_user_id_bridge():
    """Create/read browser cookie (cross-port) and mirror the ID into the Streamlit URL.

    Cookies on localhost are shared across all ports, unlike localStorage
    which is origin-scoped (port-specific).  This prevents user_id
    fragmentation when the app restarts on a different port.
    """
    embed_inline_html(
        f"""
        <script>
        (() => {{
            /* ---- cookie helpers ---- */
            function getCookie(name) {{
                const match = document.cookie.match(
                    new RegExp('(?:^|; )' + name + '=([^;]*)')
                );
                return match ? decodeURIComponent(match[1]) : null;
            }}
            function setCookie(name, value, days) {{
                const expires = new Date(
                    Date.now() + days * 864e5
                ).toUTCString();
                document.cookie = name + '=' + encodeURIComponent(value)
                    + '; expires=' + expires
                    + '; path=/; SameSite=Lax';
            }}

            /* ---- identity resolution: cookie → localStorage → generate ---- */
            const key = "{LOCAL_STORAGE_USER_ID_KEY}";
            let id = getCookie(key)
                  || window.localStorage.getItem(key);

            if (!id) {{
                const randomId = (
                    window.crypto && window.crypto.randomUUID
                ) ? window.crypto.randomUUID() : (
                    Date.now().toString(36) + "-"
                    + Math.random().toString(36).slice(2)
                );
                id = "user_" + randomId;
            }}

            /* dual-write: cookie (cross-port) + localStorage (compat) */
            setCookie(key, id, 365);
            window.localStorage.setItem(key, id);

            /* mirror to URL query params for Python to read */
            const parentUrl = new URL(window.parent.location.href);
            if (parentUrl.searchParams.get(key) !== id) {{
                parentUrl.searchParams.set(key, id);
                window.parent.history.replaceState(null, "", parentUrl.toString());
                window.parent.location.reload();
            }}
        }})();
        </script>
        """,
        height=0,
    )


def get_persistent_user_id(
    state=None,
    local_storage_id=LOCAL_STORAGE_UNSET,
    generate_uuid=None,
    query_params=None,
):
    """
    Return only a browser-confirmed analytics ID.

    Streamlit session fallback IDs are intentionally not created here because
    analytics must not write to Google Sheets until browser localStorage is ready.
    """
    active_state = state if state is not None else st.session_state
    browser_value = local_storage_id
    if browser_value is LOCAL_STORAGE_UNSET:
        browser_value = get_query_param_user_id(query_params)

    stored_id = normalize_user_id(browser_value)
    if stored_id:
        active_state["user_id"] = stored_id
        active_state["local_storage_user_id"] = stored_id
        return stored_id

    existing_id = normalize_user_id(active_state.get("local_storage_user_id", ""))
    if existing_id:
        active_state["user_id"] = existing_id
        return existing_id

    return ""


def reset_browser_user_id():
    """Clear the persistent browser user ID from cookie and localStorage."""
    embed_inline_html(
        f"""
        <script>
        /* clear cookie by setting expired date */
        document.cookie = "{LOCAL_STORAGE_USER_ID_KEY}="
            + "; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/";
        window.localStorage.removeItem("{LOCAL_STORAGE_USER_ID_KEY}");
        const parentUrl = new URL(window.parent.location.href);
        parentUrl.searchParams.delete("{LOCAL_STORAGE_USER_ID_KEY}");
        window.parent.history.replaceState(null, "", parentUrl.toString());
        window.parent.location.reload();
        </script>
        """,
        height=0,
    )
    return True


def clear_session_user_id(state):
    """Remove mirrored identity values from Streamlit session state."""
    state.pop("user_id", None)
    state.pop("local_storage_user_id", None)
    state.pop("user_id_source", None)
    state.pop("_last_browser_user_id", None)


def init_user_session():
    """Create or load the persistent anonymous analytics identity."""
    get_persistent_user_id()

    if "user_name" not in st.session_state:
        st.session_state.user_name = ""
    if "user_role" not in st.session_state:
        st.session_state.user_role = ROLE_OPTIONS[0]
    if "email" not in st.session_state:
        st.session_state.email = ""


def get_user_profile():
    """Read current optional user profile from session state."""
    return {
        "user_id": get_persistent_user_id(),
        "name": st.session_state.get("user_name", ""),
        "role": st.session_state.get("user_role", ""),
        "email": st.session_state.get("email", "") or "N/A",
    }


def is_user_id_ready():
    """Return True only when browser localStorage has confirmed the analytics ID."""
    return bool(get_persistent_user_id())


def get_answer_mode():
    """Return selected answer mode from session state."""
    return st.session_state.get("answer_mode", "Legal")


def is_gsheets_debug_enabled():
    """Return True when Google Sheets debug output is explicitly enabled."""
    try:
        session_value = st.session_state.get("DEBUG_GSHEETS", None)
        if session_value is not None:
            return str(session_value).strip().lower() in {"1", "true", "yes", "on"}
    except Exception:
        pass

    try:
        secret_value = st.secrets.get("DEBUG_GSHEETS", False)
        return str(secret_value).strip().lower() in {"1", "true", "yes", "on"}
    except Exception:
        return False


def init_chat_state():
    """Initialize chat and answer-generation state."""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "query_history" not in st.session_state:
        st.session_state.query_history = []
    if "last_query" not in st.session_state:
        st.session_state.last_query = ""
    if "last_mode" not in st.session_state:
        st.session_state.last_mode = get_answer_mode()
    if "last_response" not in st.session_state:
        st.session_state.last_response = None


@st.cache_resource(show_spinner=False)
def connect_google_sheets():
    """Connect to Google Sheets and ensure required worksheets exist."""
    from src.utils.gsheets_logger import (
        FEEDBACK_HEADERS,
        FEEDBACK_WORKSHEET,
        QUERY_HEADERS,
        QUERIES_WORKSHEET,
        SHEET_NAME,
        get_or_create_worksheet,
        get_spreadsheet,
    )

    spreadsheet = get_spreadsheet()
    if getattr(spreadsheet, "title", SHEET_NAME) != SHEET_NAME:
        raise RuntimeError(f"Connected sheet must be named exactly {SHEET_NAME}.")

    query_sheet = get_or_create_worksheet(
        spreadsheet,
        QUERIES_WORKSHEET,
        QUERY_HEADERS,
    )
    feedback_sheet = get_or_create_worksheet(
        spreadsheet,
        FEEDBACK_WORKSHEET,
        FEEDBACK_HEADERS,
    )
    return spreadsheet, query_sheet, feedback_sheet


def log_query(
    query,
    user_id="",
    name="",
    role="",
    email="",
    answer_mode="Legal",
    confidence="N/A",
    source=QUERY_SOURCE_CHATBOT,
    query_log_path=None,
):
    """Persist a user query to Google Sheets, or CSV when a path is supplied."""
    if query_log_path is not None:
        append_csv_row(
            query_log_path,
            fieldnames=["timestamp", "user_id", "query", "role", "answer_mode", "confidence", "source"],
            row={
                "timestamp": current_timestamp(),
                "user_id": user_id,
                "query": query,
                "role": role,
                "answer_mode": answer_mode,
                "confidence": confidence,
                "source": source,
            },
        )
        return True

    try:
        from src.utils.gsheets_logger import append_query_log

        append_query_log(
            user_id=user_id,
            query=query,
            role=role,
            answer_mode=answer_mode,
            confidence=confidence,
            source=source,
        )
        return True
    except Exception:
        st.caption("Query analytics are temporarily offline. Your answer experience is unaffected.")
        return False


def get_prompt_source(prompt, suggested_prompt):
    """Return the analytics source for the active prompt path."""
    if prompt:
        return QUERY_SOURCE_CHATBOT
    if suggested_prompt:
        return QUERY_SOURCE_SUGGESTED
    return QUERY_SOURCE_CHATBOT


def get_active_prompt_and_source(prompt, suggested_prompt):
    """Return the prompt and source, giving an explicit suggested click priority."""
    if suggested_prompt:
        return suggested_prompt, QUERY_SOURCE_SUGGESTED
    if prompt:
        return prompt, QUERY_SOURCE_CHATBOT
    return "", QUERY_SOURCE_CHATBOT


def queue_suggested_query(state, query):
    """Store a clicked suggested query event for the next generation pass."""
    state[PENDING_QUERY_KEY] = query
    state[PENDING_QUERY_SOURCE_KEY] = QUERY_SOURCE_SUGGESTED


def consume_pending_query_event(state, typed_prompt=None):
    """Return the active query event and clear pending event state."""
    pending_query = state.pop(PENDING_QUERY_KEY, "")
    pending_source = state.pop(PENDING_QUERY_SOURCE_KEY, None)

    if pending_query:
        return pending_query, pending_source or QUERY_SOURCE_SUGGESTED
    if typed_prompt:
        return typed_prompt, QUERY_SOURCE_CHATBOT
    return "", QUERY_SOURCE_CHATBOT


def log_generated_query(payload, source=QUERY_SOURCE_CHATBOT):
    """Persist analytics for a successfully generated answer payload."""
    profile = get_user_profile()
    if not profile["user_id"]:
        return False

    result = payload.get("result", {})
    answer_mode = payload.get("mode") or result.get("mode") or get_answer_mode()
    return log_query(
        payload.get("prompt", ""),
        user_id=profile["user_id"],
        role=profile["role"],
        answer_mode=answer_mode,
        confidence=get_confidence_label(result.get("retrieved_docs", [])),
        source=source,
    )


def save_feedback(
    query,
    feedback,
    user_id="",
    name="",
    role="",
    email=None,
    answer_mode="Legal",
    written_feedback="",
    source="chatbot_feedback",
    feedback_path=None,
    **_ignored_profile_fields,
):
    """Persist answer feedback to Google Sheets, or CSV when a path is supplied."""
    feedback_headers = [
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
    if feedback_path is not None:
        append_csv_row(
            feedback_path,
            fieldnames=feedback_headers,
            row={
                "timestamp": current_timestamp(),
                "user_id": user_id,
                "name": name,
                "role": role,
                "query": query,
                "answer_mode": answer_mode,
                "rating": feedback,
                "written_feedback": written_feedback,
                "source": source,
            },
        )
        return True

    try:
        from src.utils.gsheets_logger import save_feedback as save_feedback_to_sheets

        save_feedback_to_sheets(
            user_id=user_id,
            name=name or "",
            role=role,
            query=query,
            answer_mode=answer_mode,
            rating=feedback,
            written_feedback=written_feedback,
            source=source,
        )
        return True
    except Exception as exc:
        if is_gsheets_debug_enabled():
            from src.utils.gsheets_logger import format_google_sheets_error

            st.error(format_google_sheets_error(exc))
            st.exception(exc)
        return False


def save_waitlist_lead(user_id, name, email, role):
    """Persist one waitlist lead to Google Sheets."""
    if not email or "@" not in email:
        st.error("Please enter a valid email address.")
        return ""

    try:
        from src.utils.gsheets_logger import save_waitlist_lead as save_lead_to_sheets

        return save_lead_to_sheets(
            user_id=user_id,
            name=name,
            email=email,
            role=role,
        )
    except Exception:
        st.warning("Waitlist signup is temporarily unavailable. Please try again shortly.")
        return ""


def count_csv_rows(path):
    """Count CSV data rows safely."""
    csv_path = Path(path)
    if not csv_path.exists() or csv_path.stat().st_size == 0:
        return 0

    try:
        return len(pd.read_csv(csv_path))
    except (pd.errors.EmptyDataError, OSError):
        return 0


def read_csv_safely(path):
    """Read a CSV if present; otherwise return an empty dataframe."""
    csv_path = Path(path)
    if not csv_path.exists() or csv_path.stat().st_size == 0:
        return pd.DataFrame()

    try:
        return pd.read_csv(csv_path)
    except (pd.errors.EmptyDataError, OSError):
        return pd.DataFrame()


def calculate_feedback_percent(feedback_df, feedback_value):
    """Calculate percentage for one feedback value."""
    if feedback_df.empty:
        return 0.0

    if "rating" in feedback_df.columns:
        feedback_column = "rating"
    elif "feedback" in feedback_df.columns:
        feedback_column = "feedback"
    else:
        return 0.0

    total_feedback = len(feedback_df)
    if total_feedback == 0:
        return 0.0

    feedback_count = (feedback_df[feedback_column] == feedback_value).sum()
    return round((feedback_count / total_feedback) * 100, 1)


def load_usage_stats(query_log_path=None, feedback_path=None):
    """Load sidebar usage metrics from Sheets, or CSV paths when supplied."""
    if query_log_path is None and feedback_path is None:
        from src.utils.gsheets_logger import calculate_usage_stats

        _, query_sheet, feedback_sheet = connect_google_sheets()
        query_records = query_sheet.get_all_records()
        feedback_records = feedback_sheet.get_all_records()
        return calculate_usage_stats(query_records, feedback_records)

    query_log_path = query_log_path or QUERY_LOG_PATH
    feedback_path = feedback_path or FEEDBACK_PATH
    query_df = read_csv_safely(query_log_path)
    feedback_df = read_csv_safely(feedback_path)
    unique_users = 0
    if not query_df.empty and "user_id" in query_df.columns:
        unique_users = int(query_df["user_id"].nunique())

    return {
        "total_queries": len(query_df),
        "unique_users": unique_users,
        "total_feedback": len(feedback_df),
        "useful_feedback_percent": calculate_feedback_percent(feedback_df, "useful"),
        "not_useful_feedback_percent": calculate_feedback_percent(feedback_df, "not_useful"),
    }


def build_impact_stats(stats):
    """Build demo-safe impact metrics from live usage stats."""
    query_count = int(stats.get("total_queries", 0) or 0)
    useful_percent = float(stats.get("useful_feedback_percent", 0.0) or 0.0)
    unique_users = int(stats.get("unique_users", 0) or 0)

    query_value = f"{max(query_count, Settings.fallback_query_count)}+"
    helpful_value = f"{int(round(useful_percent or Settings.fallback_helpful_percent))}%"
    tester_value = str(unique_users) if unique_users else "Active law student testing"

    return [
        ("Legal Queries Processed", query_value),
        ("Helpful Responses", helpful_value),
        ("Active Testers", tester_value),
        ("Grounding", "Real judgments"),
    ]


def get_user_facing_error_message(exc):
    """Convert internal failures into polished user-facing copy."""
    error_text = str(exc or "")
    normalized = error_text.lower()

    if "429" in normalized or "rate" in normalized or "busy" in normalized:
        return "⚠️ SpaceL AI is experiencing high demand. Retrying with backup model support when available."
    if "vectorstore" in normalized or "index.faiss" in normalized or "retriev" in normalized:
        return "📚 No strong legal precedent index is available yet. Please build the judgment index or try again after setup."
    if "connection" in normalized or "timeout" in normalized or "network" in normalized or "temporary" in normalized:
        return "🌐 Temporary connection issue. Please try again in a few seconds."
    if "openrouter" in normalized or "ollama" in normalized or "model" in normalized or "api" in normalized:
        return "⚠️ The AI model is temporarily unavailable. SpaceL AI is keeping your session intact, so you can retry safely."
    if "no documents" in normalized or "not found" in normalized:
        return "📚 No strong legal precedent found. Try a more specific legal question."
    return "⚖️ SpaceL AI could not complete this request. Please try again with a more specific legal question."


def truncate_query(query, max_chars=60):
    """Shorten sidebar queries without losing readability."""
    query_text = str(query)
    if len(query_text) <= max_chars:
        return query_text
    return f"{query_text[: max_chars - 3]}..."


def get_recent_unique_queries(history, limit=5, max_chars=60):
    """Return last unique queries, newest first, truncated for sidebar display."""
    recent_queries = []
    seen = set()

    for query in reversed(history or []):
        normalized = str(query).strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        recent_queries.append(truncate_query(normalized, max_chars=max_chars))
        if len(recent_queries) == limit:
            break

    return recent_queries


@st.cache_resource(show_spinner=False)
def initialize_graph():
    """Load persisted FAISS index and compile the SpaceL AI graph."""
    from src.agent.graph_builder import GraphBuilder
    from src.config import Settings, get_llm
    from src.retrieval.vectorstore import get_retriever, load_vectorstore

    vectorstore = load_vectorstore(Settings.vectorstore_dir)
    retriever = get_retriever(vectorstore, k=Settings.retriever_k)
    graph = GraphBuilder(retriever=retriever, llm=get_llm())
    graph.build()
    return graph


def render_key_insight(sections):
    """Render the top-level answer takeaway."""
    insight = build_key_insight(sections)
    st.markdown(
        f"""
        <div class="insight-box">
            <strong>Key Insight</strong><br>
            {insight}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_answer_card(title, content):
    """Render one answer section as a compact professional card."""
    icon = SECTION_ICONS.get(title, "")
    try:
        card = st.container(border=True)
    except TypeError:
        card = st.container()

    with card:
        st.markdown(f"**{icon} {title}**")
        st.markdown(content)


def is_source_evidence_title(title):
    """Return True for answer sections that contain source evidence."""
    return title in {"Source Evidence", "Simplified Source Evidence"}


def render_answer_sections(answer, mode="Legal", source_filter="all"):
    """Render model output as separated legal research sections."""
    is_student_mode = mode == "Student"
    section_titles = STUDENT_SECTION_TITLES if is_student_mode else SECTION_TITLES
    sections = parse_structured_answer(answer, titles=section_titles)
    rendered_any = False

    for title in section_titles:
        content = sections.get(title, "").strip()
        if not content:
            continue
        is_source_section = is_source_evidence_title(title)
        if source_filter == "exclude" and is_source_section:
            continue
        if source_filter == "only" and not is_source_section:
            continue
        if is_source_section:
            content = sort_source_evidence(content)

        render_answer_card(title, content)
        rendered_any = True
        if title != section_titles[-1] and source_filter == "all":
            st.divider()

    return rendered_any


def render_legal_disclaimer():
    """Render the legal disclaimer below a generated answer."""
    st.markdown(
        f"""
        <div class="legal-disclaimer">
            {LEGAL_DISCLAIMER_TEXT}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_confidence_indicator(docs):
    """Display confidence based on number of retrieved documents."""
    confidence = get_confidence_label(docs)
    doc_count = len(docs or [])
    if confidence == "High":
        st.success(f"High confidence ({doc_count} documents retrieved)")
    elif confidence == "Medium":
        st.warning(f"Medium confidence ({doc_count} documents retrieved)")
    else:
        st.info(
            "⚖️ Limited direct case context found. SpaceL AI will provide the best grounded explanation available."
        )


def get_confidence_label(docs):
    """Return the compact confidence label saved with query analytics."""
    doc_count = len(docs or [])
    if doc_count >= 4:
        return "High"
    if doc_count >= 2:
        return "Medium"
    return "Low"


def render_retrieved_documents(docs):
    """Show every retrieved source chunk in original retrieval order."""
    render_source_evidence_section(docs)


def render_copy_answer(answer):
    """Render markdown copy block in a collapsed bottom expander."""
    with st.expander("Copy full answer"):
        st.code(answer, language="markdown")


def render_feedback_controls(prompt, response_id, answer_mode="Legal"):
    """Render rating and written feedback controls."""
    user_id_ready = is_user_id_ready()
    profile = get_user_profile() if user_id_ready else {"user_id": "", "name": "", "role": ""}
    feedback_key = get_feedback_key(profile["user_id"], prompt, answer_mode)
    feedback_state = get_feedback_state(st.session_state, feedback_key)
    text_key = f"feedback_text_{feedback_key}"

    st.markdown("### Was this answer helpful?")
    if feedback_state["submitted"]:
        st.success("✅ Thank you! Your feedback has been submitted.")
        return

    useful_col, not_useful_col = st.columns(2)

    with useful_col:
        if st.button(
            "👍 Helpful",
            key=f"helpful_btn_{feedback_key}",
            use_container_width=True,
            disabled=not user_id_ready,
        ):
            feedback_state = update_feedback_state(st.session_state, feedback_key, rating="helpful")

    with not_useful_col:
        if st.button(
            "👎 Not Helpful",
            key=f"not_helpful_btn_{feedback_key}",
            use_container_width=True,
            disabled=not user_id_ready,
        ):
            feedback_state = update_feedback_state(st.session_state, feedback_key, rating="not_helpful")

    selected_rating = feedback_state.get("rating")
    if selected_rating == "helpful":
        st.caption("Selected: Helpful")
    elif selected_rating == "not_helpful":
        st.caption("Selected: Not Helpful")

    if text_key not in st.session_state:
        st.session_state[text_key] = feedback_state.get("text", "")

    written_feedback = st.text_area(
        "Help me improve: What worked? What was confusing? Would you come back?",
        key=text_key,
        placeholder="Type your feedback here…",
    )
    update_feedback_state(st.session_state, feedback_key, text=written_feedback)

    submitted = st.button(
        "Submit Feedback",
        key=f"submit_feedback_{feedback_key}",
        use_container_width=True,
        disabled=not user_id_ready or not selected_rating or feedback_state["submitted"],
    )

    if submitted:
        rating_for_sheet = "useful" if selected_rating == "helpful" else "not_useful"
        if save_feedback(
            prompt,
            rating_for_sheet,
            user_id=profile["user_id"],
            name=profile["name"],
            role=profile["role"],
            answer_mode=answer_mode,
            written_feedback=written_feedback,
        ):
            mark_feedback_submitted(st.session_state, feedback_key)
            st.success("✅ Thank you! Your feedback has been submitted.")
            st.rerun()
        else:
            st.caption("Feedback could not be saved. Please try again.")

    if not user_id_ready:
        st.caption("Preparing user ID... please wait.")


def render_assistant_response(result, prompt, elapsed, response_id):
    """Render the complete professional response view."""
    answer_mode = result.get("mode", "Legal")
    render_confidence_indicator(result["retrieved_docs"])
    render_answer_sections(result["answer"], mode=answer_mode, source_filter="exclude")
    render_legal_disclaimer()
    render_feedback_controls(prompt, response_id, answer_mode=answer_mode)
    if render_answer_sections(result["answer"], mode=answer_mode, source_filter="only"):
        st.divider()
    render_retrieved_documents(result["retrieved_docs"])
    render_copy_answer(result["answer"])
    st.success(f"Response generated in {elapsed:.2f}s")


def render_llm_error(exc):
    """Render a clean LLM provider error instead of a traceback."""
    st.warning(get_user_facing_error_message(exc))


def run_graph_with_mode(graph, prompt, mode):
    """Run graph, clearing stale Streamlit cache if an old graph is loaded."""
    try:
        return graph.run(prompt, mode=mode)
    except TypeError as exc:
        if "unexpected keyword argument 'mode'" not in str(exc):
            raise

        initialize_graph.clear()
        fresh_graph = initialize_graph()
        return fresh_graph.run(prompt, mode=mode)


def set_graph_stream_callback(graph, token_callback=None):
    """Attach a temporary streaming callback when the active LLM supports it."""
    llm = getattr(graph, "llm", None)
    setter = getattr(llm, "set_stream_callback", None)
    if callable(setter):
        setter(token_callback)


def log_response_timing(result, elapsed):
    """Print before/after response timing breakdown for performance tracking."""
    timings = result.get("timings", {}) if isinstance(result, dict) else {}
    retrieval_time = float(timings.get("retrieval_time", 0.0) or 0.0)
    llm_time = float(timings.get("llm_time", 0.0) or 0.0)
    total_response_time = float(timings.get("total_response_time", elapsed) or elapsed)
    print(
        "SpaceL AI performance | before: ~38.00s | "
        f"after: {elapsed:.2f}s | retrieval: {retrieval_time:.2f}s | "
        f"llm: {llm_time:.2f}s | total: {total_response_time:.2f}s"
    )


def generate_response_payload(graph, prompt, mode, token_callback=None):
    """Generate one answer payload for the prompt/mode pair."""
    start_time = time.time()
    set_graph_stream_callback(graph, token_callback)
    try:
        result = run_graph_with_mode(graph, prompt, mode)
    finally:
        set_graph_stream_callback(graph, None)
    elapsed = time.time() - start_time
    log_response_timing(result, elapsed)
    return {
        "result": result,
        "prompt": prompt,
        "mode": mode,
        "elapsed": elapsed,
        "response_id": str(time.time_ns()),
    }


def get_loading_message(mode, is_regeneration=False):
    """Return a concise loading message for the current answer path."""
    if is_regeneration:
        return f"Preparing grounded {mode.lower()} answer..."
    if mode == "Student":
        return "Preparing grounded student explanation..."
    return "Analyzing legal precedents..."


def remember_last_response(payload, mode):
    """Store the latest generated answer for automatic mode switching."""
    st.session_state.last_query = payload["prompt"]
    st.session_state.last_mode = mode
    st.session_state.last_response = payload


def replace_last_assistant_response(payload):
    """Replace the latest assistant result without duplicating the chat."""
    assistant_message = {
        "role": "assistant",
        "content": payload["result"]["answer"],
        "result": payload["result"],
        "prompt": payload["prompt"],
        "elapsed": payload["elapsed"],
        "response_id": payload["response_id"],
    }

    for index in range(len(st.session_state.messages) - 1, -1, -1):
        if st.session_state.messages[index].get("role") == "assistant":
            st.session_state.messages[index] = assistant_message
            return

    st.session_state.messages.append(assistant_message)


def regenerate_on_mode_change(graph):
    """Regenerate the stored query when the user changes answer mode."""
    current_mode = get_answer_mode()
    previous_mode = st.session_state.get("last_mode", current_mode)
    last_query = st.session_state.get("last_query", "")

    if not last_query or current_mode == previous_mode:
        return

    with st.spinner(get_loading_message(current_mode, is_regeneration=True)):
        payload = generate_response_payload(graph, last_query, current_mode)

    remember_last_response(payload, current_mode)
    replace_last_assistant_response(payload)
    log_generated_query(payload, source=QUERY_SOURCE_MODE_REGENERATION)


def render_landing_metric(label, value):
    """Render a compact landing-page proof metric."""
    st.markdown(
        f"""
        <div class="landing-metric">
            <strong>{value}</strong><br>
            <span>{label}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def get_landing_stats():
    """Load live impact stats, falling back to demo-safe values."""
    try:
        return load_usage_stats()
    except Exception:
        return EMPTY_USAGE_STATS


def render_impact_section():
    """Show credible live or fallback traction metrics."""
    st.markdown('<div class="landing-section">', unsafe_allow_html=True)
    st.markdown('<div class="landing-section-title">📈 SpaceL AI Impact</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="landing-section-copy">Helping law students simplify legal research with transparent, source-backed answers.</div>',
        unsafe_allow_html=True,
    )

    metric_columns = st.columns(4)
    for column, (label, value) in zip(metric_columns, build_impact_stats(get_landing_stats())):
        with column:
            render_landing_metric(label, value)
    st.markdown("</div>", unsafe_allow_html=True)


def render_card_grid(title, subtitle, items, columns=3):
    """Render a simple startup-style card grid."""
    st.markdown('<div class="landing-section">', unsafe_allow_html=True)
    st.markdown(f'<div class="landing-section-title">{title}</div>', unsafe_allow_html=True)
    if subtitle:
        st.markdown(f'<div class="landing-section-copy">{subtitle}</div>', unsafe_allow_html=True)

    grid_columns = st.columns(columns)
    for index, (item_title, body) in enumerate(items):
        with grid_columns[index % columns]:
            st.markdown(
                f"""
                <div class="landing-card">
                    <strong>{item_title}</strong><br><br>
                    {body}
                </div>
                """,
                unsafe_allow_html=True,
            )
    st.markdown("</div>", unsafe_allow_html=True)


def render_use_cases():
    """Render common query areas as compact pills."""
    st.markdown('<div class="landing-section">', unsafe_allow_html=True)
    st.markdown('<div class="landing-section-title">Built for High-Frequency Criminal Law Questions</div>', unsafe_allow_html=True)
    use_cases = [
        "✔ Bail conditions",
        "✔ Benefit of doubt",
        "✔ Circumstantial evidence",
        "✔ Criminal appeals",
        "✔ Sentencing",
    ]
    columns = st.columns(len(use_cases))
    for column, use_case in zip(columns, use_cases):
        with column:
            st.markdown(f'<div class="use-case-pill">{use_case}</div>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)


def render_waitlist_form():
    """Collect early-access leads from the landing page."""
    user_id_ready = is_user_id_ready()
    st.markdown("### Get early access to SpaceL AI")
    with st.form("waitlist_form", clear_on_submit=False):
        name = st.text_input("Name (optional)", key="waitlist_name")
        email = st.text_input("Email", key="waitlist_email")
        role = st.selectbox("Role", ROLE_OPTIONS, key="waitlist_role")
        submitted = st.form_submit_button("Join Waitlist", use_container_width=True, disabled=not user_id_ready)

    if not user_id_ready:
        st.caption("Preparing user ID... please wait.")

    if not submitted:
        return

    waitlist_result = save_waitlist_lead(
        get_persistent_user_id(),
        name.strip(),
        email.strip(),
        role,
    )
    if waitlist_result:
        st.session_state.email = email.strip()
        if name.strip():
            st.session_state.user_name = name.strip()
        st.session_state.user_role = role
        if waitlist_result == "created":
            st.success("You're on the SpaceL AI early access list.")
        else:
            st.success("You're already on the SpaceL AI early access list.")


def render_landing_page():
    """Render the startup-style MVP landing page before the RAG chat."""
    st.markdown(
        f"""
        <section class="landing-hero">
            <div class="landing-kicker">🚀 AI legal research in seconds</div>
            <h1 class="landing-title">{PRODUCT_NAME}</h1>
            <div class="landing-tagline">
                SpaceL AI helps law students and legal professionals understand
                criminal judgments using grounded AI.
            </div>
            <p class="landing-copy">
                Ask a legal question, retrieve real Supreme Court judgment passages,
                and get structured reasoning with transparent source evidence.
            </p>
        </section>
        """,
        unsafe_allow_html=True,
    )

    cta_col, demo_col, _ = st.columns([1.1, 1.2, 3])
    with cta_col:
        if st.button("Try SpaceL AI", type="primary", use_container_width=True):
            st.session_state.show_app_section = True
            st.success("SpaceL AI is ready below. Ask a legal research question to begin.")
    with demo_col:
        st.link_button("Watch 60-sec Demo", Settings.demo_video_url, use_container_width=True)

    st.markdown('<div class="landing-section">', unsafe_allow_html=True)
    st.markdown('<div class="landing-section-title">🎥 Watch SpaceL AI in Action</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="landing-section-copy">See how legal research becomes faster using grounded AI over real judgments.</div>',
        unsafe_allow_html=True,
    )
    st.video(Settings.demo_video_url)
    st.markdown("</div>", unsafe_allow_html=True)

    render_card_grid(
        "How It Works",
        "A simple workflow designed for fast legal research demos.",
        [
            ("1️⃣ Ask a legal question", "Type a question about bail, evidence, appeals, sentencing, or benefit of doubt."),
            ("2️⃣ AI retrieves real judgments", "SpaceL AI searches the existing FAISS judgment index for relevant passages."),
            ("3️⃣ Get grounded reasoning", "Receive structured legal reasoning with source evidence you can inspect."),
        ],
        columns=3,
    )

    render_use_cases()

    render_card_grid(
        "Why Trust SpaceL AI?",
        "Built to make legal AI feel transparent, cautious, and useful.",
        [
            ("📚 Grounded in Court Judgments", "Answers are generated from retrieved judgment passages, not generic web text."),
            ("⚖️ Legal Reasoning Support", "Legal Mode organizes issues, reasoning, takeaways, and evidence."),
            ("🎓 Student-Friendly Mode", "Student Mode explains concepts in plain English while staying source-grounded."),
            ("🔍 Transparent Source Evidence", "Every answer keeps retrieved documents visible for review."),
        ],
        columns=4,
    )

    render_impact_section()
    render_waitlist_form()
    st.markdown('<div class="app-anchor" id="ask-spacel-ai"></div>', unsafe_allow_html=True)


def render_sidebar():
    """Render public controls and lightweight usage metrics."""
    with st.sidebar:
        st.markdown("## SpaceL AI")
        st.caption("Grounded criminal-law research assistant")

        st.markdown("---")
        st.markdown("## Answer Mode")
        st.radio(
            "Mode",
            ANSWER_MODE_OPTIONS,
            key="answer_mode",
            horizontal=True,
        )

        st.markdown("---")
        st.markdown("## Recent Searches")
        recent_queries = get_recent_unique_queries(st.session_state.get("query_history", []))
        if recent_queries:
            for query in recent_queries:
                st.markdown(f"- {query}")
        else:
            st.caption("No searches yet.")

        st.markdown("---")
        st.markdown("## Usage Stats")
        try:
            connect_google_sheets()
            st.success("Google Sheets connected")
            stats = load_usage_stats()
        except Exception as exc:
            from src.utils.gsheets_logger import format_google_sheets_error

            st.info("Live analytics are temporarily unavailable.")
            st.caption(format_google_sheets_error(exc))
            try:
                from src.utils.gsheets_logger import get_service_account_email

                service_account_email = get_service_account_email()
                if service_account_email:
                    st.caption(f"Share the SpaceL AI analytics sheet with: {service_account_email}")
                else:
                    st.caption("Share the sheet with the service account email and check credentials.")
            except Exception:
                st.caption("Share the sheet with the service account email and check credentials.")
            stats = EMPTY_USAGE_STATS

        st.metric("Total Queries", stats["total_queries"])
        st.metric("Unique Users", stats["unique_users"])
        st.metric("Feedback Count", stats["total_feedback"])
        st.metric("Useful Feedback %", f"{stats['useful_feedback_percent']:.1f}%")
        st.metric("Not Useful Feedback %", f"{stats['not_useful_feedback_percent']:.1f}%")

        st.markdown("---")
        if st.button("New Query", use_container_width=True):
            st.session_state.messages = []
            st.session_state.query_history = []
            st.session_state.last_query = ""
            st.session_state.last_mode = get_answer_mode()
            st.session_state.last_response = None
            for key in list(st.session_state.keys()):
                if str(key).startswith(
                    (
                        "feedback_submitted_",
                        "feedback_rating_",
                        "feedback_text_",
                        "helpful_btn_",
                        "not_helpful_btn_",
                        "submit_feedback_",
                    )
                ):
                    del st.session_state[key]
            st.session_state.feedback_states = {}
            st.rerun()


def render_suggested_queries(disabled=False):
    """Render suggested query buttons and queue the clicked query event."""
    st.markdown("### Try these:")
    columns = st.columns([1, 1, 1], gap="small")
    for index, suggested_query in enumerate(SUGGESTED_QUERIES):
        with columns[index]:
            button_label = SUGGESTED_QUERY_LABELS[index]
            if st.button(button_label, key=f"suggested_query_{index}", use_container_width=True, disabled=disabled):
                queue_suggested_query(st.session_state, suggested_query)


def main():
    """Render the chat interface."""
    render_user_id_bridge()
    init_user_session()
    init_chat_state()
    user_id_ready = is_user_id_ready()

    render_landing_page()

    st.title("SpaceL AI")
    st.markdown(
        '<p class="legal-subtitle">Criminal case research assistant powered by Supreme Court judgments (2008-2023)</p>',
        unsafe_allow_html=True,
    )

    if not user_id_ready:
        st.info("Preparing user ID... please wait.")

    render_suggested_queries(disabled=not user_id_ready)

    try:
        graph = initialize_graph()
        st.success("Judgment index loaded. SpaceL AI is ready.")
    except Exception as exc:
        st.warning(get_user_facing_error_message(exc))
        st.info("Run `python scripts/build_index.py` before starting the UI.")
        render_sidebar()
        return

    try:
        regenerate_on_mode_change(graph)
    except Exception as exc:
        render_llm_error(exc)
        render_sidebar()
        return

    for message_index, message in enumerate(st.session_state.messages):
        with st.chat_message(message["role"]):
            if message["role"] == "assistant" and message.get("result"):
                render_assistant_response(
                    message["result"],
                    message.get("prompt", ""),
                    message.get("elapsed", 0.0),
                    message.get("response_id", f"history_{message_index}"),
                )
            else:
                st.markdown(message["content"])

    prompt = st.chat_input(
        "Ask SpaceL AI about criminal appeals, bail, evidence, sentencing...",
        disabled=not user_id_ready,
    )
    active_prompt, query_source = consume_pending_query_event(st.session_state, typed_prompt=prompt)
    if not active_prompt:
        render_sidebar()
        return

    if not user_id_ready:
        st.info("Preparing user ID... please wait.")
        render_sidebar()
        return

    st.session_state.query_history.append(active_prompt)

    st.session_state.messages.append({"role": "user", "content": active_prompt})
    with st.chat_message("user"):
        st.markdown(active_prompt)

    with st.chat_message("assistant"):
        st.caption("Retrieving legal precedents...")
        streamed_answer = []
        stream_placeholder = st.empty()

        def show_streamed_token(token):
            streamed_answer.append(token)
            stream_placeholder.markdown("".join(streamed_answer))

        with st.spinner(get_loading_message(get_answer_mode())):
            try:
                payload = generate_response_payload(
                    graph,
                    active_prompt,
                    get_answer_mode(),
                    token_callback=show_streamed_token,
                )
            except Exception as exc:
                render_llm_error(exc)
                render_sidebar()
                return

        stream_placeholder.empty()
        if not log_generated_query(payload, source=query_source):
            st.caption("Query analytics will sync after the browser user ID is ready.")
        render_assistant_response(
            payload["result"],
            payload["prompt"],
            payload["elapsed"],
            payload["response_id"],
        )

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": payload["result"]["answer"],
            "result": payload["result"],
            "prompt": payload["prompt"],
            "elapsed": payload["elapsed"],
            "response_id": payload["response_id"],
        }
    )
    remember_last_response(payload, get_answer_mode())
    render_sidebar()


if __name__ == "__main__":
    main()
