"""Giao diện web tra cứu pháp luật lao động."""

from __future__ import annotations

import tempfile
import uuid
from pathlib import Path
from typing import Any, Optional

import streamlit as st

from Adaptive_RAG.config import AdaptiveRAGConfig
from Adaptive_RAG.pipeline.adaptive_pipeline import AdaptiveRAGPipeline
from CRAG.config import CRAGConfig
from RAG.corrective.config import CRAGConfig as CorrectiveRAGConfig
from RAG.corrective.corrective_rag import CorrectiveRAGPipeline
from RAG.pipeline.config import PipelineConfig
from RAG.pipeline.traditional_rag import TraditionalRAGPipeline
from storage.schema import HistoryFilter
from storage.query_history import QueryHistoryDatabase


MODES = {
    "Cơ bản": "baseline",
    "Hiệu chỉnh": "corrective",
    "Thích ứng": "adaptive",
}

SAMPLE_QUESTIONS = [
    "Thời giờ làm việc bình thường của người lao động là bao nhiêu?",
    "Người lao động làm việc 5 năm thì được bao nhiêu ngày nghỉ phép năm?",
    "So sánh quy định về thời giờ làm việc và làm thêm giờ trong Bộ luật Lao động 2019 và Nghị định 145/2020.",
]

THEMES = {
    "Trắng / Kem sáng": {
        "background": "#fbfcfa",
        "surface": "#ffffff",
        "sidebar": "#f3f6f3",
        "text": "#1d2b24",
        "muted": "#64736a",
        "accent": "#245b45",
        "accent_soft": "#eaf1ec",
        "border": "#e4e9e5",
        "hover": "#f5f8f5",
    },
    "Vàng nhạt / Sepia": {
        "background": "#f4ecd8",
        "surface": "#fbf5e8",
        "sidebar": "#eee3cb",
        "text": "#3e3426",
        "muted": "#76684f",
        "accent": "#805c2e",
        "accent_soft": "#e9dcc0",
        "border": "#ded1b8",
        "hover": "#f0e5cf",
    },
}


st.set_page_config(
    page_title="Tra cứu pháp luật lao động",
    page_icon="§",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_resource(show_spinner=False)
def get_history_db() -> QueryHistoryDatabase:
    return QueryHistoryDatabase()


@st.cache_resource(show_spinner=False)
def get_pipeline(
    mode: str,
    provider: str,
    model_name: Optional[str],
    top_k: int,
    similarity_threshold: float,
) -> Any:
    pipeline_config = PipelineConfig(
        TOP_K=top_k,
        SIMILARITY_THRESHOLD=similarity_threshold,
        LLM_PROVIDER=provider,
        LLM_MODEL=model_name,
        TEMPERATURE=0.0,
        ENABLE_PRE_GUARD=True,
        ENABLE_POST_GUARD=True,
    )

    if mode == "baseline":
        return TraditionalRAGPipeline(config=pipeline_config)

    if mode == "corrective":
        corrective_config = CorrectiveRAGConfig(
            TOP_K=top_k,
            SIMILARITY_THRESHOLD=similarity_threshold,
            LLM_PROVIDER=provider,
            LLM_MODEL=model_name or "mock-legal-generator-v1",
            TEMPERATURE=0.0,
            ENABLE_PRE_GUARD=True,
            ENABLE_POST_GUARD=True,
        )
        return CorrectiveRAGPipeline(config=corrective_config)

    if mode == "adaptive":
        return AdaptiveRAGPipeline(
            config=AdaptiveRAGConfig(
                ENABLE_DIRECT_ROUTING=True,
                MAX_SUB_QUERIES=4,
            ),
            pipeline_config=pipeline_config,
            crag_config=CRAGConfig(
                TOP_K=top_k,
                SIMILARITY_THRESHOLD=similarity_threshold,
            ),
        )

    raise ValueError(f"Chế độ tra cứu không hợp lệ: {mode}")


def get_value(item: Any, key: str, default: Any = None) -> Any:
    if isinstance(item, dict):
        return item.get(key, default)
    return getattr(item, key, default)


def enum_text(value: Any) -> str:
    return str(getattr(value, "value", value)) if value is not None else ""


def citation_label(citation: Any) -> str:
    if isinstance(citation, str):
        return citation
    return (
        get_value(citation, "formatted_citation")
        or get_value(citation, "document_title")
        or get_value(citation, "citation")
        or "Nguồn tham khảo"
    )


def render_citations(citations: list[Any]) -> None:
    if not citations:
        return

    st.markdown("#### Căn cứ pháp lý")
    for index, citation in enumerate(citations, start=1):
        title = citation_label(citation)
        document_number = get_value(citation, "document_number")
        article_number = get_value(citation, "article_number")
        article_title = get_value(citation, "article_title")
        source_url = get_value(citation, "source_url")

        details = [str(value) for value in (document_number, article_number, article_title) if value]
        with st.container(border=True):
            st.markdown(f"**{index:02d} · {title}**")
            if details:
                st.caption(" · ".join(details))
            if source_url:
                st.link_button("Mở văn bản gốc", str(source_url))


def render_sources(chunks: list[Any]) -> None:
    if not chunks:
        return

    with st.expander(f"Tài liệu đã tra cứu · {len(chunks)}"):
        for index, chunk in enumerate(chunks, start=1):
            metadata = get_value(chunk, "metadata", {}) or {}
            document = (
                metadata.get("document_title")
                or metadata.get("document_id")
                or get_value(chunk, "document_id")
                or "Văn bản pháp luật"
            )
            article = metadata.get("article_number") or get_value(chunk, "article_number")
            score = get_value(chunk, "score")
            heading = f"{index:02d} · {document}"
            if article:
                heading += f" · Điều {article}"
            if score is not None:
                heading += f" · độ phù hợp {float(score):.2f}"

            with st.container(border=True):
                st.markdown(f"**{heading}**")
                content = get_value(chunk, "content") or get_value(chunk, "content_snippet", "")
                if content:
                    st.markdown(str(content))


def render_trace(response: Any, mode: str) -> None:
    items: list[tuple[str, str]] = []

    if mode == "adaptive":
        classification = get_value(response, "classification")
        trace = get_value(response, "trace")
        if classification:
            items.extend(
                [
                    ("Nhánh xử lý", enum_text(get_value(response, "route_taken"))),
                    ("Ý định", enum_text(get_value(classification, "intent"))),
                    ("Độ phức tạp", enum_text(get_value(classification, "complexity"))),
                ]
            )
            reasoning = get_value(classification, "reasoning")
            if reasoning:
                items.append(("Lý do phân loại", str(reasoning)))

        plan = get_value(trace, "plan") if trace else None
        sub_queries = get_value(plan, "sub_queries", []) if plan else []
        if sub_queries:
            items.append(
                ("Các bước tra cứu", "\n".join(f"- {get_value(query, 'text', query)}" for query in sub_queries))
            )
    elif mode == "corrective":
        evaluation = get_value(response, "initial_evaluation")
        if evaluation:
            items.extend(
                [
                    ("Đánh giá lượt đầu", enum_text(get_value(evaluation, "status"))),
                    (
                        "Hiệu chỉnh truy vấn",
                        "Đã thực hiện" if get_value(response, "corrective_triggered") else "Không cần thiết",
                    ),
                ]
            )
            rewritten_query = get_value(response, "rewritten_query")
            if rewritten_query:
                items.append(("Truy vấn hiệu chỉnh", str(rewritten_query)))
    else:
        items.append(("Nhánh xử lý", "Truy xuất ngữ nghĩa"))

    if items:
        with st.expander("Thông tin xử lý"):
            for label, value in items:
                st.markdown(f"**{label}**")
                st.markdown(value)


def render_response(response: Any, mode: str) -> None:
    answer = get_value(response, "answer", "")
    if get_value(response, "refused", False):
        st.info(answer)
        reason = get_value(response, "refusal_reason")
        if reason:
            st.caption(str(reason))
    else:
        st.markdown(answer)

    latency = (
        get_value(response, "latency_ms")
        or get_value(response, "latency")
        or get_value(get_value(response, "telemetry"), "total_latency")
        or 0
    )
    citations = get_value(response, "citations", []) or []
    chunks = get_value(response, "retrieved_chunks", []) or []

    metric_columns = st.columns(3)
    metric_columns[0].metric("Thời gian xử lý", f"{float(latency):,.0f} ms")
    metric_columns[1].metric("Nguồn đã dùng", len(chunks))
    metric_columns[2].metric("Trích dẫn", len(citations))

    render_citations(citations)
    render_sources(chunks)
    render_trace(response, mode)


def run_query(
    question: str,
    mode: str,
    provider: str,
    model_name: Optional[str],
    top_k: int,
    similarity_threshold: float,
    save_history: bool,
) -> None:
    st.session_state.messages.append({"role": "user", "content": question})
    try:
        with st.spinner("Đang tra cứu văn bản pháp luật..."):
            pipeline = get_pipeline(mode, provider, model_name, top_k, similarity_threshold)
            response = pipeline.answer(question)

        st.session_state.current_title = st.session_state.get("current_title") or question
        history_error = None
        if save_history:
            try:
                history_db = get_history_db()
                session_id = st.session_state.session_id
                history_db.ensure_chat_session(session_id, question)
                if mode == "baseline":
                    history_db.log_rag_response(response, session_id=session_id)
                elif mode == "corrective":
                    history_db.log_crag_response(response, session_id=session_id)
                else:
                    history_db.log_adaptive_response(response, session_id=session_id)
            except Exception as error:
                history_error = str(error)

        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": get_value(response, "answer", ""),
                "response": response,
                "mode": mode,
                "history_error": history_error,
            }
        )
    except Exception as error:
        st.session_state.messages.append(
            {"role": "assistant", "content": str(error), "error": True}
        )


def load_chat_session(history_db: QueryHistoryDatabase, session_id: str) -> list[dict[str, Any]]:
    records = history_db.get_history(HistoryFilter(session_id=session_id, limit=10000))
    messages = []
    for record in reversed(records):
        messages.append({"role": "user", "content": record.query})
        mode = (
            "adaptive"
            if "Adaptive" in record.model_name
            else "corrective"
            if record.model_name == "CRAG"
            else "baseline"
        )
        response = {
            "answer": record.answer,
            "citations": record.citations,
            "retrieved_chunks": record.retrieved_chunks,
            "latency": record.total_latency_ms,
            "refused": record.is_refused,
            "refusal_reason": record.refusal_reason,
        }
        messages.append(
            {
                "role": "assistant",
                "content": record.answer,
                "response": response,
                "mode": mode,
                "history_record_id": record.id,
            }
        )
    return messages


def export_history(history_db: QueryHistoryDatabase, file_format: str) -> bytes:
    suffix = ".json" if file_format == "JSON" else ".csv"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as export_file:
        export_path = Path(export_file.name)
    try:
        if file_format == "JSON":
            history_db.export_to_json(export_path)
        else:
            history_db.export_to_csv(export_path)
        return export_path.read_bytes()
    finally:
        export_path.unlink(missing_ok=True)


def render_history_tools(history_db: QueryHistoryDatabase) -> None:
    st.subheader("Thống kê tổng quan")
    stats = history_db.get_statistics()
    metrics = st.columns(4)
    metrics[0].metric("Tổng câu hỏi", f"{stats.total_queries:,}")
    metrics[1].metric("Từ chối", f"{stats.total_refusals:,}", f"{stats.refusal_rate:.1%}")
    metrics[2].metric("Độ trễ trung bình", f"{stats.avg_total_latency_ms:,.0f} ms")
    metrics[3].metric("Chi phí ước tính", f"${stats.total_estimated_cost_usd:.6f}")
    st.caption(f"Token trung bình mỗi câu: {stats.avg_total_tokens:,.1f}")

    distribution_tab, records_tab, export_tab = st.tabs(
        ["Phân bổ", "Tìm kiếm & chi tiết", "Xuất & đánh giá"]
    )
    with distribution_tab:
        model_column, route_column = st.columns(2)
        with model_column:
            st.markdown("**Theo mô hình**")
            if stats.queries_by_model:
                st.bar_chart(stats.queries_by_model, horizontal=True)
            else:
                st.caption("Chưa có dữ liệu.")
        with route_column:
            st.markdown("**Theo nhánh xử lý**")
            if stats.queries_by_route:
                st.bar_chart(stats.queries_by_route, horizontal=True)
            else:
                st.caption("Chưa có dữ liệu.")

    with records_tab:
        search_column, limit_column = st.columns([3, 1])
        with search_column:
            keyword = st.text_input(
                "Tìm trong câu hỏi và câu trả lời",
                placeholder="Ví dụ: thử việc, nghỉ phép...",
                key="history_record_search",
            )
        with limit_column:
            record_limit = st.selectbox("Số bản ghi", [10, 20, 50, 100], key="history_record_limit")
        records = history_db.get_history(
            HistoryFilter(search_keyword=keyword.strip() or None, limit=record_limit)
        )
        if records:
            st.dataframe(
                [
                    {
                        "ID": record.id,
                        "Thời gian": record.timestamp[:19].replace("T", " "),
                        "Mô hình": record.model_name,
                        "Nhánh": record.route_taken or "—",
                        "Câu hỏi": record.query,
                        "Từ chối": "Có" if record.is_refused else "Không",
                        "Đánh giá": f"{record.user_rating}/5" if record.user_rating is not None else "Chưa đánh giá",
                        "Nhận xét": record.user_feedback or "—",
                    }
                    for record in records
                ],
                width="stretch",
                hide_index=True,
            )
            record_ids = [record.id for record in records if record.id is not None]
            selected_record_id = st.selectbox(
                "Xem chi tiết bản ghi",
                record_ids,
                format_func=lambda record_id: (
                    f"#{record_id} · "
                    f"{next(record.query for record in records if record.id == record_id)[:85]}"
                ),
                key="history_record_id",
            )
            detail_is_open = st.session_state.get("view_history_record") == selected_record_id
            if st.button(
                "Đóng chi tiết" if detail_is_open else "Mở chi tiết",
                key="toggle_history_record",
            ):
                st.session_state.view_history_record = None if detail_is_open else selected_record_id
                st.rerun()
            if detail_is_open:
                record = history_db.get_record(selected_record_id)
                if record:
                    with st.container(border=True):
                        st.caption(
                            f"Bản ghi #{record.id} · {record.timestamp} · "
                            f"{record.model_name} · {record.total_latency_ms:,.0f} ms"
                        )
                        st.markdown(f"**Câu hỏi**\n\n{record.query}")
                        st.markdown(f"**Câu trả lời**\n\n{record.answer}")
                        st.caption(
                            f"Token: {record.total_tokens:,} · "
                            f"Chi phí ước tính: ${record.estimated_cost_usd:.6f}"
                        )
                        if record.user_rating is not None:
                            st.caption(
                                f"Đánh giá: {record.user_rating}/5"
                                + (f" · {record.user_feedback}" if record.user_feedback else "")
                            )
        else:
            st.info("Không tìm thấy bản ghi phù hợp." if keyword else "Chưa có lịch sử tra cứu.")

    with export_tab:
        st.markdown("Tải lịch sử truy vấn để lưu trữ hoặc phân tích.")
        json_column, csv_column = st.columns(2)
        with json_column:
            if st.button("Chuẩn bị JSON", width="stretch"):
                st.session_state.history_export = export_history(history_db, "JSON")
                st.session_state.history_export_format = "JSON"
            if st.session_state.get("history_export_format") == "JSON":
                st.download_button(
                    "Tải xuống JSON",
                    data=st.session_state.history_export,
                    file_name="history.json",
                    mime="application/json",
                    width="stretch",
                )
        with csv_column:
            if st.button("Chuẩn bị CSV", width="stretch"):
                st.session_state.history_export = export_history(history_db, "CSV")
                st.session_state.history_export_format = "CSV"
            if st.session_state.get("history_export_format") == "CSV":
                st.download_button(
                    "Tải xuống CSV",
                    data=st.session_state.history_export,
                    file_name="history.csv",
                    mime="text/csv",
                    width="stretch",
                )

        st.divider()
        st.markdown("**Đánh giá câu trả lời**")
        rateable_records = history_db.get_history(HistoryFilter(limit=100))
        rateable_ids = [record.id for record in rateable_records if record.id is not None]
        if rateable_ids:
            feedback_id = st.selectbox(
                "Bản ghi cần đánh giá",
                rateable_ids,
                format_func=lambda record_id: (
                    f"#{record_id} · "
                    f"{next(record.query for record in rateable_records if record.id == record_id)[:70]}"
                ),
                key="feedback_record_id",
            )
            feedback_record = history_db.get_record(feedback_id)
            if feedback_record:
                rating_key = f"feedback_rating_{feedback_id}"
                feedback_key = f"feedback_text_{feedback_id}"
                with st.form(f"history_feedback_form_{feedback_id}"):
                    rating = st.slider(
                        "Điểm",
                        min_value=1,
                        max_value=5,
                        value=feedback_record.user_rating or 5,
                        key=rating_key,
                    )
                    feedback = st.text_area(
                        "Nhận xét",
                        value=feedback_record.user_feedback or "",
                        placeholder="Chia sẻ góp ý về câu trả lời",
                        key=feedback_key,
                    )
                    submitted = st.form_submit_button("Lưu đánh giá")
                if feedback_record.user_rating is not None:
                    st.caption(
                        f"Đang lưu: {feedback_record.user_rating}/5"
                        + (f" · {feedback_record.user_feedback}" if feedback_record.user_feedback else "")
                    )
                if st.session_state.get("feedback_saved_id") == feedback_id:
                    st.success(f"Đã lưu đánh giá cho bản ghi #{feedback_id}.")
                    st.session_state.feedback_saved_id = None
                if submitted:
                    updated = history_db.update_feedback(
                        feedback_id,
                        user_rating=rating,
                        user_feedback=feedback.strip() or None,
                    )
                    if updated:
                        st.session_state.feedback_saved_id = feedback_id
                        st.rerun()
                    else:
                        st.error(f"Không tìm thấy bản ghi #{feedback_id}.")
        else:
            st.caption("Chưa có bản ghi để đánh giá.")


if "messages" not in st.session_state:
    st.session_state.messages = []
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

history_db = get_history_db()
if st.session_state.get("reader_theme") not in THEMES:
    st.session_state.reader_theme = "Trắng / Kem sáng"
theme_name = st.session_state.get("reader_theme", "Trắng / Kem sáng")
theme = THEMES.get(theme_name, THEMES["Trắng / Kem sáng"])
theme_variables = "\n".join(f"--{name}: {color};" for name, color in theme.items())
st.markdown(
    f"""
    <style>
    :root {{
        {theme_variables}
        color-scheme: light;
    }}
    html, body {{ color-scheme: light; }}
    .stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"] {{
        background: var(--background); color: var(--text);
    }}
    [data-testid="stHeader"] {{
        background: var(--background); color: var(--text);
        border-bottom: 1px solid var(--border);
    }}
    [data-testid="stToolbar"] {{ visibility: visible; }}
    [data-testid="stSidebar"] {{
        background: var(--sidebar); color: var(--text);
        border-right: 1px solid var(--border);
    }}
    [data-testid="stSidebar"] > div:first-child {{ padding-top: 1rem; }}
    [data-testid="stSidebarCollapsedControl"] {{
        visibility: visible !important; opacity: 1 !important;
        color: var(--text); background: var(--surface);
        border: 1px solid var(--border); border-radius: 8px;
    }}
    [data-testid="stSidebar"] button[aria-label="Collapse sidebar"] {{
        visibility: visible !important; opacity: 1 !important;
        color: var(--text); background: var(--surface);
        border: 1px solid var(--border); border-radius: 8px;
        z-index: 2;
    }}
    .block-container {{ max-width: 1050px; padding-top: 5rem; padding-bottom: 5rem; }}
    h1, h2, h3, h4, p, li, label, [data-testid="stMarkdownContainer"] {{
        color: var(--text);
    }}
    h1, h2, h3 {{ letter-spacing: -0.035em; }}
    h1 {{ font-size: 2.2rem !important; font-weight: 650 !important; }}
    [data-testid="stCaptionContainer"] p, [data-testid="stMetricLabel"] p {{
        color: var(--muted);
    }}
    [data-testid="stMetric"], [data-testid="stExpander"],
    [data-testid="stVerticalBlockBorderWrapper"] {{
        background: var(--surface); color: var(--text);
        border-color: var(--border); border-radius: 12px;
    }}
    [data-testid="stMetric"] {{ padding: 14px 16px; }}
    [data-testid="stMetricValue"] {{ color: var(--accent); font-size: 1.35rem; }}
    [data-testid="stAlert"] {{
        background: var(--accent_soft); color: var(--text);
        border: 1px solid var(--border);
    }}
    [data-testid="stMarkdownContainer"], [data-testid="stMarkdownContainer"] * {{
        color: var(--text);
    }}
    [data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] * {{
        color: var(--muted);
    }}
    input, textarea, [data-baseweb="input"] > div,
    [data-baseweb="textarea"] > div, [data-baseweb="select"] > div {{
        background: var(--surface) !important; color: var(--text) !important;
        border-color: var(--border) !important; box-shadow: none;
    }}
    input::placeholder, textarea::placeholder {{
        color: var(--muted) !important; opacity: 1;
    }}
    [data-baseweb="popover"], [data-baseweb="menu"], [role="listbox"] {{
        background: var(--surface) !important; color: var(--text) !important;
    }}
    [role="option"], [role="option"] *, [role="listbox"] * {{
        color: var(--text) !important;
    }}
    [role="option"]:hover, [role="option"][aria-selected="true"] {{
        background: var(--hover) !important;
    }}
    [role="tablist"] {{ border-color: var(--border); }}
    [role="tab"] {{ color: var(--muted); }}
    [role="tab"][aria-selected="true"] {{ color: var(--accent); }}
    [data-testid="stDataFrame"], [data-testid="stTable"] {{
        background: var(--surface); color: var(--text);
    }}
    [data-testid="stSlider"] [role="slider"] {{ background: var(--accent); }}
    .brand-mark {{
        color: var(--accent); font-size: 0.78rem; font-weight: 700;
        letter-spacing: 0.12em; text-transform: uppercase;
    }}
    .message-label {{
        color: var(--accent); font-size: 0.72rem; font-weight: 700;
        letter-spacing: 0.09em; margin-bottom: 0.55rem;
    }}
    .intro {{
        color: var(--muted); max-width: 700px; font-size: 1.02rem;
        line-height: 1.7; margin-top: -0.4rem; margin-bottom: 1.5rem;
    }}
    div.stButton > button, [data-testid="stDownloadButton"] button,
    [data-testid="stFormSubmitButton"] button {{
        border: 1px solid var(--border); border-radius: 10px;
        color: var(--text) !important; background: var(--surface) !important; min-height: 2.7rem;
        text-align: left; padding-left: 0.8rem; padding-right: 0.8rem;
        transition: border-color 120ms ease, background 120ms ease;
    }}
    div.stButton > button:hover, [data-testid="stDownloadButton"] button:hover,
    [data-testid="stFormSubmitButton"] button:hover {{
        border-color: var(--accent) !important; background: var(--hover) !important;
        color: var(--accent) !important;
    }}
    .st-key-query_bar [data-testid="stTextInput"] input {{
        min-height: 3.2rem; padding-left: 1.15rem; border-radius: 999px;
        box-shadow: 0 2px 10px rgba(30, 45, 35, 0.08);
    }}
    .st-key-query_bar [data-testid="stTextInput"] input:focus {{
        border-color: var(--accent) !important;
        box-shadow: 0 2px 12px rgba(30, 45, 35, 0.12);
    }}
    .st-key-query_bar [data-testid="stFormSubmitButton"] button {{
        min-height: 3.2rem; border-radius: 999px; text-align: center;
        font-size: 1.1rem; font-weight: 600; padding: 0;
    }}
    hr {{ border-color: var(--border); }}
    </style>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown('<div class="brand-mark">Tra cứu pháp luật</div>', unsafe_allow_html=True)
    st.selectbox("Giao diện đọc", list(THEMES), key="reader_theme")
    st.divider()

    st.markdown("### Lịch sử hội thoại")
    session_search = st.text_input(
        "Tìm hội thoại",
        placeholder="Tìm theo tiêu đề, câu hỏi, câu trả lời",
        key="chat_session_search",
        label_visibility="collapsed",
    )
    saved_sessions = history_db.get_chat_sessions(search_keyword=session_search, limit=50)
    for saved_session in saved_sessions:
        title = saved_session["title"] or "Cuộc trò chuyện"
        count = saved_session["query_count"]
        if st.button(
            f"{title[:54]}{'…' if len(title) > 54 else ''}  ·  {count}",
            key=f"load_chat_{saved_session['session_id']}",
            width="stretch",
            type="primary" if saved_session["session_id"] == st.session_state.session_id else "secondary",
        ):
            st.session_state.session_id = saved_session["session_id"]
            st.session_state.current_title = title
            st.session_state.messages = load_chat_session(history_db, saved_session["session_id"])
            st.rerun()

    active_sessions = history_db.get_chat_sessions(limit=1000)
    active_session = next(
        (item for item in active_sessions if item["session_id"] == st.session_state.session_id),
        None,
    )
    active_title = active_session["title"] if active_session else ""
    with st.form("rename_chat_form"):
        new_title = st.text_input(
            "Tiêu đề hội thoại",
            value=active_title,
            placeholder="Tiêu đề mặc định là câu hỏi đầu tiên",
            key=f"chat_title_{st.session_state.session_id}",
        )
        rename_submitted = st.form_submit_button("Đổi tiêu đề", width="stretch")
    if rename_submitted:
        if not new_title.strip():
            st.error("Tiêu đề không được để trống.")
        else:
            history_db.rename_chat_session(st.session_state.session_id, new_title)
            st.session_state.current_title = new_title.strip()
            st.success("Đã cập nhật tiêu đề.")
            st.rerun()

    if st.button("＋  Cuộc hội thoại mới", width="stretch"):
        st.session_state.messages = []
        st.session_state.session_id = str(uuid.uuid4())
        st.session_state.current_title = ""
        st.rerun()

    st.divider()
    st.markdown("### Thiết lập tra cứu")

    selected_mode = st.selectbox("Phương thức", list(MODES.keys()), index=2)
    mode = MODES[selected_mode]
    st.caption(
        {
            "baseline": "Tra cứu trực tiếp trong văn bản pháp luật.",
            "corrective": "Đánh giá và hiệu chỉnh khi kết quả ban đầu chưa đủ căn cứ.",
            "adaptive": "Tự chọn cách tra cứu phù hợp với từng câu hỏi.",
        }[mode]
    )

    provider_label = st.selectbox(
        "Bộ tạo câu trả lời",
        ["Ngoại tuyến", "OpenAI", "Gemini", "Tự động"],
        help="Chọn OpenAI hoặc Gemini nếu đã cấu hình khóa truy cập trong môi trường.",
    )
    provider = {
        "Ngoại tuyến": "mock",
        "OpenAI": "openai",
        "Gemini": "gemini",
        "Tự động": "auto",
    }[provider_label]

    with st.expander("Tùy chọn nâng cao"):
        top_k = st.slider("Số nguồn tối đa", min_value=3, max_value=10, value=5)
        similarity_threshold = st.slider(
            "Ngưỡng tương đồng",
            min_value=0.20,
            max_value=0.80,
            value=0.45,
            step=0.05,
        )
        model_name_input = st.text_input("Tên mô hình (không bắt buộc)", placeholder="Để trống để dùng mặc định")
        save_history = st.toggle("Lưu lịch sử tra cứu", value=True)

    st.caption("Nguồn dữ liệu: văn bản pháp luật lao động Việt Nam")

model_name = model_name_input.strip() or None

chat_tab, database_tab = st.tabs(["Tra cứu", "Lịch sử & dữ liệu"])
with chat_tab:
    current_title = (
        st.session_state.get("current_title")
        or (active_session["title"] if active_session else "")
        or "Cuộc trò chuyện mới"
    )
    st.markdown('<div class="brand-mark">Văn bản · Căn cứ · Tham chiếu</div>', unsafe_allow_html=True)
    st.title(current_title[:90])
    st.markdown(
        '<p class="intro">Đặt câu hỏi để tra cứu quy định pháp luật lao động Việt Nam. '
        'Câu trả lời đi kèm căn cứ và các đoạn văn bản liên quan để bạn tiện đối chiếu.</p>',
        unsafe_allow_html=True,
    )

    pending_question = st.session_state.pop("pending_question", None)
    if pending_question:
        run_query(
            question=pending_question,
            mode=mode,
            provider=provider,
            model_name=model_name,
            top_k=top_k,
            similarity_threshold=similarity_threshold,
            save_history=save_history,
        )
        st.session_state.scroll_to_latest = True

    if not st.session_state.messages:
        st.markdown("#### Bắt đầu với một câu hỏi")
        suggestion_columns = st.columns(3)
        for index, sample in enumerate(SAMPLE_QUESTIONS):
            if suggestion_columns[index].button(sample, key=f"sample_{index}", width="stretch"):
                st.session_state.pending_question = sample
                st.rerun()

    for message in st.session_state.messages:
        with st.container(border=True):
            label = "BẠN" if message["role"] == "user" else "TRA CỨU"
            st.markdown(f'<div class="message-label">{label}</div>', unsafe_allow_html=True)
            if message.get("error"):
                st.error(f"Không thể xử lý câu hỏi: {message['content']}")
            elif message["role"] == "assistant" and message.get("response") is not None:
                render_response(message["response"], message["mode"])
                if message.get("history_error"):
                    st.warning(f"Câu trả lời đã có, nhưng không lưu được lịch sử: {message['history_error']}")
            else:
                st.markdown(message["content"])

    with st.container(key="query_bar"):
        with st.form("query_form", clear_on_submit=True, border=False):
            input_column, submit_column = st.columns([8, 1.4], vertical_alignment="center")
            with input_column:
                question_draft = st.text_input(
                    "Câu hỏi",
                    placeholder="Hỏi về pháp luật lao động...",
                    label_visibility="collapsed",
                )
            with submit_column:
                question_submitted = st.form_submit_button(
                    "Tra cứu",
                    icon=":material/search:",
                    width="stretch",
                )
    if question_submitted and question_draft.strip():
        run_query(
            question=question_draft.strip(),
            mode=mode,
            provider=provider,
            model_name=model_name,
            top_k=top_k,
            similarity_threshold=similarity_threshold,
            save_history=save_history,
        )
        st.session_state.scroll_to_latest = True
        st.rerun()

    st.caption("Thông tin tham khảo; vui lòng đối chiếu với văn bản pháp luật gốc.")
    if st.session_state.pop("scroll_to_latest", False):
        st.components.v1.html(
            """
            <script>
            const main = window.parent.document.querySelector('[data-testid="stMain"]');
            if (main) {
                requestAnimationFrame(() => main.scrollTo({
                    top: main.scrollHeight,
                    behavior: "smooth"
                }));
            }
            </script>
            """,
            height=0,
            scrolling=False,
        )

with database_tab:
    render_history_tools(history_db)
