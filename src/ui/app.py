"""Streamlit UI for SpaceL AI."""

import csv
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.ui.formatting import (
    SECTION_ICONS,
    SECTION_TITLES,
    build_key_insight,
    clean_snippet,
    format_case_label,
    parse_structured_answer,
)


PROCESSED_DATA_DIR = PROJECT_ROOT / "data" / "processed"
QUERY_LOG_PATH = PROCESSED_DATA_DIR / "query_logs.csv"
FEEDBACK_PATH = PROCESSED_DATA_DIR / "feedback.csv"
PRODUCT_NAME = "SpaceL AI"
PRODUCT_TAGLINE = "Where law meets intelligence - powered by real case data."
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
    .block-container {max-width: 980px; padding-top: 2rem; padding-bottom: 7rem;}
    .legal-subtitle {color: #4b5563; margin-bottom: 1.25rem;}
    .landing-hero {
        padding: 2rem 0 1.25rem 0;
        border-bottom: 1px solid #e5e7eb;
        margin-bottom: 1.5rem;
    }
    .landing-kicker {
        color: #2563eb;
        font-weight: 700;
        letter-spacing: .02em;
        text-transform: uppercase;
        font-size: .8rem;
        margin-bottom: .5rem;
    }
    .landing-title {
        font-size: clamp(2.5rem, 6vw, 4.6rem);
        line-height: 1;
        margin: 0 0 .75rem 0;
        font-weight: 800;
        color: #111827;
    }
    .landing-tagline {
        color: #1f2937;
        font-size: 1.2rem;
        margin-bottom: .75rem;
    }
    .landing-copy {
        color: #4b5563;
        font-size: 1rem;
        max-width: 680px;
    }
    .landing-card {
        border: 1px solid #e5e7eb;
        background: #ffffff;
        border-radius: 8px;
        padding: 1rem;
        min-height: 140px;
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
        background: #eff6ff;
        border-radius: 8px;
        padding: .85rem;
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


def init_user_session():
    """Create lightweight anonymous session identity."""
    if "user_id" not in st.session_state:
        st.session_state.user_id = str(uuid.uuid4())
    if "user_name" not in st.session_state:
        st.session_state.user_name = ""
    if "user_role" not in st.session_state:
        st.session_state.user_role = ROLE_OPTIONS[0]
    if "email" not in st.session_state:
        st.session_state.email = ""


def get_user_profile():
    """Read current optional user profile from session state."""
    return {
        "user_id": st.session_state.get("user_id", ""),
        "name": st.session_state.get("user_name", ""),
        "role": st.session_state.get("user_role", ""),
        "email": st.session_state.get("email", "") or "N/A",
    }


def get_answer_mode():
    """Return selected answer mode from session state."""
    return st.session_state.get("answer_mode", "Legal")


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


def log_query(query, user_id="", name="", role="", email="", query_log_path=None):
    """Persist a user query to Google Sheets, or CSV when a path is supplied."""
    if query_log_path is not None:
        append_csv_row(
            query_log_path,
            fieldnames=["timestamp", "user_id", "name", "email", "role", "query"],
            row={
                "timestamp": current_timestamp(),
                "user_id": user_id,
                "name": name,
                "email": email or "N/A",
                "role": role,
                "query": query,
            },
        )
        return True

    try:
        _, query_sheet, _ = connect_google_sheets()
        query_sheet.append_row(
            [
                current_timestamp(),
                user_id,
                name,
                email or "N/A",
                role,
                query,
            ]
        )
        return True
    except Exception as exc:
        st.error(f"Google Sheets query logging failed: {exc}")
        return False


def save_feedback(
    query,
    feedback,
    user_id="",
    name="",
    role="",
    email=None,
    feedback_path=None,
    **_ignored_profile_fields,
):
    """Persist answer feedback to Google Sheets, or CSV when a path is supplied."""
    if feedback_path is not None:
        append_csv_row(
            feedback_path,
            fieldnames=["timestamp", "user_id", "name", "role", "query", "feedback"],
            row={
                "timestamp": current_timestamp(),
                "user_id": user_id,
                "name": name,
                "role": role,
                "query": query,
                "feedback": feedback,
            },
        )
        return True

    try:
        _, _, feedback_sheet = connect_google_sheets()
        feedback_sheet.append_row(
            [
                current_timestamp(),
                user_id,
                name,
                role,
                query,
                feedback,
            ]
        )
        return True
    except Exception as exc:
        st.error(f"Google Sheets feedback logging failed: {exc}")
        return False


def save_waitlist_lead(user_id, name, email, role):
    """Persist one landing-page waitlist lead to Google Sheets."""
    if not email or "@" not in email:
        st.error("Please enter a valid email address.")
        return False

    try:
        from src.utils.gsheets_logger import save_waitlist_lead as save_lead_to_sheets

        save_lead_to_sheets(
            user_id=user_id,
            name=name,
            email=email,
            role=role,
        )
        return True
    except Exception as exc:
        st.error(f"Waitlist signup failed: {exc}")
        return False


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
    if feedback_df.empty or "feedback" not in feedback_df.columns:
        return 0.0

    total_feedback = len(feedback_df)
    if total_feedback == 0:
        return 0.0

    feedback_count = (feedback_df["feedback"] == feedback_value).sum()
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


def render_answer_sections(answer):
    """Render model output as separated legal research sections."""
    sections = parse_structured_answer(answer)
    render_key_insight(sections)

    for title in SECTION_TITLES:
        content = sections.get(title, "").strip()
        if not content:
            continue

        icon = SECTION_ICONS.get(title, "")
        st.markdown('<div class="section-gap"></div>', unsafe_allow_html=True)
        st.markdown(f"### {icon} {title}")
        st.markdown(content)


def render_confidence_indicator(docs):
    """Display confidence based on number of retrieved documents."""
    doc_count = len(docs or [])
    if doc_count >= 4:
        st.success(f"High confidence ({doc_count} documents retrieved)")
    elif doc_count >= 2:
        st.warning(f"Moderate confidence ({doc_count} documents retrieved)")
    else:
        st.error(f"Low confidence ({doc_count} documents retrieved)")


def render_retrieved_documents(docs):
    """Show every retrieved source chunk in original retrieval order."""
    st.markdown('<div class="section-gap"></div>', unsafe_allow_html=True)
    st.markdown("### Retrieved Documents")

    if not docs:
        st.info("No documents retrieved.")
        return

    for source_number, doc in enumerate(docs, start=1):
        label = format_case_label(doc, source_number=source_number)
        metadata = getattr(doc, "metadata", {}) or {}

        with st.expander(label):
            source = metadata.get("source") or "Unknown source"
            st.caption(f"File path: {source}")
            st.markdown("**Retrieved snippet:**")
            st.markdown(clean_snippet(getattr(doc, "page_content", "")))


def render_copy_answer(answer):
    """Render markdown copy block in a collapsed bottom expander."""
    with st.expander("Copy full answer"):
        st.code(answer, language="markdown")


def render_law_student_explanation(result, response_id):
    """Render optional simplified explanation for law students."""
    explanation_key = f"law_student_explanation_{response_id}"
    if st.session_state.get(explanation_key):
        st.markdown('<div class="section-gap"></div>', unsafe_allow_html=True)
        st.markdown("### Simplified Explanation")
        st.markdown(st.session_state[explanation_key])
        return

    if st.button(
        "Explain for Law Student",
        key=f"explain_law_student_{response_id}",
        use_container_width=True,
    ):
        try:
            from src.agent.explainer import explain_answer_for_law_students
            from src.config import get_llm

            with st.spinner("Simplifying for law students..."):
                explanation = explain_answer_for_law_students(
                    get_llm(),
                    result.get("retrieved_docs", []),
                    result.get("answer", ""),
                )
            st.session_state[explanation_key] = explanation
            st.markdown('<div class="section-gap"></div>', unsafe_allow_html=True)
            st.markdown("### Simplified Explanation")
            st.markdown(explanation)
        except Exception as exc:
            render_llm_error(exc)


def render_feedback_controls(prompt, response_id):
    """Render useful/not useful feedback buttons."""
    submitted_key = f"feedback_submitted_{response_id}"
    if st.session_state.get(submitted_key):
        st.caption("Feedback recorded. Thank you.")
        return

    st.markdown("### Feedback")
    useful_col, not_useful_col = st.columns(2)

    with useful_col:
        if st.button("Useful", key=f"useful_{response_id}", use_container_width=True):
            profile = get_user_profile()
            if save_feedback(
                prompt,
                "useful",
                user_id=profile["user_id"],
                name=profile["name"],
                role=profile["role"],
            ):
                st.session_state[submitted_key] = True
                st.success("Feedback saved to Google Sheets: useful")

    with not_useful_col:
        if st.button("Not Useful", key=f"not_useful_{response_id}", use_container_width=True):
            profile = get_user_profile()
            if save_feedback(
                prompt,
                "not_useful",
                user_id=profile["user_id"],
                name=profile["name"],
                role=profile["role"],
            ):
                st.session_state[submitted_key] = True
                st.warning("Feedback saved to Google Sheets: not useful")


def render_assistant_response(result, prompt, elapsed, response_id):
    """Render the complete professional response view."""
    render_confidence_indicator(result["retrieved_docs"])
    render_answer_sections(result["answer"])
    if result.get("mode") == "Legal":
        render_law_student_explanation(result, response_id)
    render_retrieved_documents(result["retrieved_docs"])
    render_copy_answer(result["answer"])
    render_feedback_controls(prompt, response_id)
    st.success(f"Response generated in {elapsed:.2f}s")


def render_llm_error(exc):
    """Render a clean LLM provider error instead of a traceback."""
    error_text = str(exc)
    if "429" in error_text or "rate-limit" in error_text.lower() or "rate limited" in error_text.lower():
        st.warning(
            "OpenRouter is temporarily rate-limited for all configured free models. "
            "Please wait a few minutes and try again, or configure a paid/BYOK model."
        )
    else:
        st.error(f"OpenRouter failed: {error_text}")


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


def render_landing_social_proof():
    """Show MVP usage proof, preferring live Sheets metrics when available."""
    st.markdown("### MVP Proof")
    try:
        stats = load_usage_stats()
        metric_columns = st.columns(4)
        with metric_columns[0]:
            render_landing_metric("Total queries", stats["total_queries"])
        with metric_columns[1]:
            render_landing_metric("Unique users", stats["unique_users"])
        with metric_columns[2]:
            render_landing_metric("Feedback count", stats["total_feedback"])
        with metric_columns[3]:
            render_landing_metric("Useful feedback", f"{stats['useful_feedback_percent']:.1f}%")
    except Exception:
        proof_columns = st.columns(4)
        proof_items = [
            "18+ queries tested",
            "10+ users already using",
            "Real case-based reasoning",
            "Feedback-driven improvements",
        ]
        for column, item in zip(proof_columns, proof_items):
            with column:
                render_landing_metric("", item)


def render_waitlist_form():
    """Collect early-access leads from the landing page."""
    st.markdown("### Get early access to SpaceL AI")
    with st.form("waitlist_form", clear_on_submit=False):
        name = st.text_input("Name (optional)", key="waitlist_name")
        email = st.text_input("Email", key="waitlist_email")
        role = st.selectbox("Role", ROLE_OPTIONS, key="waitlist_role")
        submitted = st.form_submit_button("Join Waitlist", use_container_width=True)

    if not submitted:
        return

    if save_waitlist_lead(
        st.session_state.get("user_id", ""),
        name.strip(),
        email.strip(),
        role,
    ):
        st.session_state.email = email.strip()
        if name.strip():
            st.session_state.user_name = name.strip()
        st.session_state.user_role = role
        st.success("You're on the SpaceL AI early access list.")


def render_landing_page():
    """Render the startup-style MVP landing page before the RAG chat."""
    st.markdown(
        f"""
        <section class="landing-hero">
            <div class="landing-kicker">AI legal research assistant</div>
            <h1 class="landing-title">{PRODUCT_NAME}</h1>
            <div class="landing-tagline">{PRODUCT_TAGLINE}</div>
            <p class="landing-copy">
                Ask legal questions and get case-based answers instantly.
                No more hours of searching judgments or reading long PDFs.
            </p>
        </section>
        """,
        unsafe_allow_html=True,
    )

    if st.button("Try SpaceL AI", type="primary", use_container_width=False):
        st.session_state.show_app_section = True
        st.success("SpaceL AI is ready below. Ask a legal research question to begin.")

    st.markdown("### Demo")
    st.video("https://youtu.be/a5OXVLpDyH4")
    st.caption("See how SpaceL AI answers real legal questions in seconds.")

    problem_col, solution_col = st.columns(2)
    with problem_col:
        st.markdown("### Problem")
        st.markdown(
            """
            Legal research is slow, complex, and inefficient.

            Students and lawyers spend hours:
            - Searching through multiple judgments
            - Reading long legal documents
            - Trying to find relevant reasoning
            - Missing key case insights
            """
        )

    with solution_col:
        st.markdown("### Solution")
        st.markdown(
            """
            SpaceL AI simplifies legal research.

            Just ask a question and get:
            - Clear legal issue breakdown
            - Relevant case context
            - Source-backed reasoning
            - Easy explanations for students
            """
        )

    st.markdown("### Product Experience")
    experience_col, output_col = st.columns([1, 1])
    with experience_col:
        st.markdown(
            """
            <div class="landing-card">
                <strong>Example query</strong><br><br>
                Benefit of doubt in criminal appeals
            </div>
            """,
            unsafe_allow_html=True,
        )
    with output_col:
        st.markdown(
            """
            <div class="landing-card">
                <strong>Expected output</strong><br><br>
                Legal Issue<br>
                Key Insight<br>
                Relevant Case Context<br>
                Source Documents
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("### Core Features")
    feature_columns = st.columns(4)
    features = [
        ("Legal Mode", "Professional legal reasoning"),
        ("Student Mode", "Explain like a law student"),
        ("Case-backed Answers", "Powered by real Supreme Court judgments"),
        ("Instant Insights", "Get answers in seconds"),
    ]
    for column, (title, body) in zip(feature_columns, features):
        with column:
            st.markdown(
                f"""
                <div class="landing-card">
                    <strong>{title}</strong><br><br>
                    {body}
                </div>
                """,
                unsafe_allow_html=True,
            )

    render_landing_social_proof()
    render_waitlist_form()
    st.markdown('<div class="app-anchor" id="ask-spacel-ai"></div>', unsafe_allow_html=True)


def render_sidebar():
    """Render recent searches, usage metrics, and reset control."""
    with st.sidebar:
        st.markdown("## User Details")
        st.text_input("Name (optional)", key="user_name")
        st.selectbox("Role", ROLE_OPTIONS, key="user_role")
        email = st.text_input("Enter your email (optional)", key="email")
        if not email:
            st.info("Enter your email to get updates and improvements")

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

            st.error(f"Google Sheets failed: {format_google_sheets_error(exc)}")
            try:
                from src.utils.gsheets_logger import get_service_account_email

                service_account_email = get_service_account_email()
                if service_account_email:
                    st.caption(f"Share `Legal_Vakta_Logs` with: {service_account_email}")
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
            for key in list(st.session_state.keys()):
                if str(key).startswith("feedback_submitted_"):
                    del st.session_state[key]
            st.rerun()


def render_suggested_queries():
    """Render suggested query buttons and return the clicked query."""
    st.markdown("### Try these:")
    columns = st.columns([1, 1, 1], gap="small")
    for index, suggested_query in enumerate(SUGGESTED_QUERIES):
        with columns[index]:
            button_label = SUGGESTED_QUERY_LABELS[index]
            if st.button(button_label, key=f"suggested_query_{index}", use_container_width=True):
                return suggested_query
    return None


def main():
    """Render the chat interface."""
    init_user_session()

    render_landing_page()

    st.title("SpaceL AI - Criminal Case Assistant")
    st.markdown(
        '<p class="legal-subtitle">Knowledge Base: Supreme Court Criminal Judgments (2008-2023)</p>',
        unsafe_allow_html=True,
    )

    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "query_history" not in st.session_state:
        st.session_state.query_history = []

    suggested_prompt = render_suggested_queries()

    try:
        graph = initialize_graph()
        st.success("Vector index loaded. SpaceL AI is ready.")
    except Exception as exc:
        st.error(str(exc))
        st.info("Run `python scripts/build_index.py` before starting the UI.")
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

    prompt = st.chat_input("Ask about criminal appeals, conviction, bail, sentencing, evidence...")
    active_prompt = prompt or suggested_prompt
    if not active_prompt:
        render_sidebar()
        return

    profile = get_user_profile()
    log_query(active_prompt, **profile)
    st.session_state.query_history.append(active_prompt)

    st.session_state.messages.append({"role": "user", "content": active_prompt})
    with st.chat_message("user"):
        st.markdown(active_prompt)

    with st.chat_message("assistant"):
        with st.spinner("Analyzing legal documents..."):
            start_time = time.time()
            try:
                result = run_graph_with_mode(graph, active_prompt, get_answer_mode())
            except Exception as exc:
                render_llm_error(exc)
                render_sidebar()
                return
            elapsed = time.time() - start_time
            response_id = str(time.time_ns())

        render_assistant_response(result, active_prompt, elapsed, response_id)

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": result["answer"],
            "result": result,
            "prompt": active_prompt,
            "elapsed": elapsed,
            "response_id": response_id,
        }
    )
    render_sidebar()


if __name__ == "__main__":
    main()
