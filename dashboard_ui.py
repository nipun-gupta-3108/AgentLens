import html
import os
import re
import time
from datetime import datetime
from urllib.parse import urlparse

import streamlit as st

from agents import critic_chain
from pipeline import extract_score, generate_report, revise_report
from tools import get_search_results, scrape_url


PIPELINE_STAGES = [
    ("search", "Search", "Find reliable web results"),
    ("scrape", "Scrape", "Read top source pages"),
    ("writer", "Writer", "Draft grounded report"),
    ("critic", "Critic", "Evaluate research quality"),
    ("revision", "Revision", "Improve when needed"),
]


def configure_page() -> None:
    st.set_page_config(
        page_title="ResearchMind | AI Research Workspace",
        page_icon="🔬",
        layout="wide",
        initial_sidebar_state="expanded",
    )


def inject_styles() -> None:
    st.markdown(
        """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap');

:root {
    --bg: #080b11;
    --panel: #0d121c;
    --panel-2: #111827;
    --line: rgba(148, 163, 184, 0.18);
    --text: #eef4ff;
    --muted: #9aa7bb;
    --subtle: #68758b;
    --accent: #5eead4;
    --accent-2: #60a5fa;
    --good: #34d399;
    --warn: #fbbf24;
    --bad: #fb7185;
}

html, body, [class*="css"] {
    font-family: Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    color: var(--text);
}

.stApp {
    background:
        radial-gradient(circle at 18% 0%, rgba(94, 234, 212, 0.12), transparent 28rem),
        radial-gradient(circle at 88% 18%, rgba(139, 92, 246, 0.13), transparent 30rem),
        linear-gradient(180deg, #080b11 0%, #0b1018 45%, #080b11 100%);
}

#MainMenu, header, footer { visibility: hidden; }

.block-container {
    max-width: 1440px;
    padding: 1.4rem 2rem 3rem;
}

section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, rgba(9, 13, 21, 0.98), rgba(13, 18, 28, 0.98));
    border-right: 1px solid var(--line);
}

div[data-testid="stSidebarNav"] { display: none; }

.app-shell {
    display: flex;
    flex-direction: column;
    gap: 1.1rem;
}

.topbar {
    display: flex;
    align-items: flex-end;
    justify-content: space-between;
    gap: 1rem;
    border-bottom: 1px solid var(--line);
    padding-bottom: 1rem;
    margin-bottom: 0.4rem;
}

.eyebrow {
    color: var(--accent);
    font-family: "JetBrains Mono", monospace;
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.16em;
    text-transform: uppercase;
}

.topbar h1 {
    color: var(--text);
    font-size: clamp(2rem, 4vw, 3.8rem);
    line-height: 1.02;
    letter-spacing: 0;
    margin: 0.35rem 0 0;
}

.topbar p {
    color: var(--muted);
    max-width: 740px;
    margin: 0.65rem 0 0;
    line-height: 1.65;
}

.status-pill {
    border: 1px solid var(--line);
    background: rgba(17, 24, 39, 0.82);
    border-radius: 999px;
    color: var(--muted);
    font-family: "JetBrains Mono", monospace;
    font-size: 0.76rem;
    padding: 0.55rem 0.82rem;
    white-space: nowrap;
}

.metric-grid {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 0.85rem;
    margin: 0.65rem 0 1rem;
}

.metric-card, .workspace-card, .doc-section, .quality-card, .source-card, .empty-state {
    background: linear-gradient(180deg, rgba(17, 24, 39, 0.9), rgba(10, 15, 23, 0.92));
    border: 1px solid var(--line);
    border-radius: 8px;
    box-shadow: 0 18px 60px rgba(0, 0, 0, 0.24);
}

.metric-card {
    padding: 1rem;
    min-height: 6.15rem;
}

.metric-label {
    color: var(--subtle);
    font-family: "JetBrains Mono", monospace;
    font-size: 0.7rem;
    letter-spacing: 0.12em;
    text-transform: uppercase;
}

.metric-value {
    color: var(--text);
    font-size: 1.85rem;
    font-weight: 800;
    line-height: 1.1;
    margin-top: 0.45rem;
}

.metric-note {
    color: var(--muted);
    font-size: 0.82rem;
    margin-top: 0.28rem;
}

.workspace-card {
    padding: 1.15rem;
    margin-bottom: 0.8rem;
}

.workspace-title {
    color: var(--text);
    font-size: 1rem;
    font-weight: 750;
    margin-bottom: 0.2rem;
}

.workspace-caption {
    color: var(--muted);
    font-size: 0.9rem;
    line-height: 1.55;
}

.stTextArea textarea, .stTextInput input {
    background: rgba(8, 11, 17, 0.88) !important;
    border: 1px solid rgba(148, 163, 184, 0.2) !important;
    border-radius: 8px !important;
    color: var(--text) !important;
    box-shadow: none !important;
}

.stTextArea textarea:focus, .stTextInput input:focus {
    border-color: rgba(94, 234, 212, 0.64) !important;
    box-shadow: 0 0 0 3px rgba(94, 234, 212, 0.1) !important;
}

label, .stTextArea label, .stTextInput label {
    color: var(--muted) !important;
    font-weight: 650 !important;
}

.stButton > button, .stDownloadButton > button {
    border-radius: 8px !important;
    border: 1px solid rgba(94, 234, 212, 0.3) !important;
    background: linear-gradient(135deg, #5eead4 0%, #60a5fa 100%) !important;
    color: #071016 !important;
    font-weight: 800 !important;
    min-height: 2.75rem;
    box-shadow: 0 12px 34px rgba(94, 234, 212, 0.16) !important;
}

.stButton > button[kind="secondary"], .stDownloadButton > button[kind="secondary"] {
    background: rgba(17, 24, 39, 0.85) !important;
    color: var(--text) !important;
    border-color: var(--line) !important;
    box-shadow: none !important;
}

.stButton > button:disabled {
    opacity: 0.55;
}

.stage-track {
    display: grid;
    grid-template-columns: repeat(5, minmax(0, 1fr));
    gap: 0.7rem;
    margin: 0.55rem 0 1.1rem;
}

.stage-card {
    background: rgba(17, 24, 39, 0.76);
    border: 1px solid var(--line);
    border-radius: 8px;
    min-height: 7.2rem;
    padding: 0.9rem;
    position: relative;
}

.stage-card.done { border-color: rgba(52, 211, 153, 0.46); }
.stage-card.running { border-color: rgba(94, 234, 212, 0.72); background: rgba(20, 184, 166, 0.1); }
.stage-card.error { border-color: rgba(251, 113, 133, 0.62); }
.stage-card.skipped { border-color: rgba(251, 191, 36, 0.34); }

.stage-index {
    color: var(--subtle);
    font-family: "JetBrains Mono", monospace;
    font-size: 0.68rem;
    letter-spacing: 0.11em;
}

.stage-name {
    color: var(--text);
    font-size: 1rem;
    font-weight: 800;
    margin-top: 0.32rem;
}

.stage-desc {
    color: var(--muted);
    font-size: 0.78rem;
    line-height: 1.4;
    margin-top: 0.32rem;
}

.stage-state {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    color: var(--muted);
    font-family: "JetBrains Mono", monospace;
    font-size: 0.67rem;
    margin-top: 0.75rem;
    text-transform: uppercase;
}

.stage-dot {
    width: 0.45rem;
    height: 0.45rem;
    border-radius: 999px;
    background: var(--subtle);
}

.done .stage-dot { background: var(--good); }
.running .stage-dot { background: var(--accent); }
.error .stage-dot { background: var(--bad); }
.skipped .stage-dot { background: var(--warn); }

.doc-section {
    padding: 1.2rem 1.35rem;
    margin-bottom: 0.85rem;
}

.doc-section h3 {
    color: var(--text);
    font-size: 1.05rem;
    margin: 0 0 0.65rem;
}

.doc-section .content {
    color: #d7deea;
    font-size: 0.95rem;
    line-height: 1.72;
}

.quality-card {
    padding: 1.15rem;
    border-color: rgba(94, 234, 212, 0.28);
}

.score-ring {
    display: flex;
    align-items: baseline;
    gap: 0.35rem;
}

.score-value {
    color: var(--accent);
    font-size: 3rem;
    font-weight: 850;
    letter-spacing: 0;
}

.score-total {
    color: var(--subtle);
    font-size: 1.2rem;
    font-weight: 700;
}

.score-verdict {
    color: var(--muted);
    line-height: 1.52;
}

.feedback-list {
    background: rgba(8, 11, 17, 0.55);
    border: 1px solid var(--line);
    border-radius: 8px;
    padding: 0.85rem 1rem;
    margin-bottom: 0.8rem;
}

.feedback-list h4 {
    color: var(--text);
    margin: 0 0 0.45rem;
    font-size: 0.92rem;
}

.feedback-list ul {
    margin: 0;
    padding-left: 1.05rem;
    color: #cbd5e1;
    line-height: 1.58;
    font-size: 0.9rem;
}

.source-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 0.8rem;
}

.source-card {
    padding: 1rem;
    min-height: 9.5rem;
}

.source-domain {
    color: var(--accent);
    font-family: "JetBrains Mono", monospace;
    font-size: 0.72rem;
    word-break: break-word;
}

.source-title {
    color: var(--text);
    font-size: 0.98rem;
    font-weight: 760;
    margin-top: 0.45rem;
    line-height: 1.35;
}

.source-snippet {
    color: var(--muted);
    font-size: 0.86rem;
    line-height: 1.55;
    margin-top: 0.45rem;
}

.source-card a {
    color: #93c5fd !important;
    text-decoration: none;
    font-size: 0.82rem;
    overflow-wrap: anywhere;
}

.empty-state {
    padding: 2.2rem;
    text-align: center;
    color: var(--muted);
}

.empty-state strong {
    color: var(--text);
    display: block;
    font-size: 1.1rem;
    margin-bottom: 0.35rem;
}

.sidebar-brand {
    border-bottom: 1px solid var(--line);
    padding-bottom: 1rem;
    margin-bottom: 1rem;
}

.sidebar-brand h2 {
    color: var(--text);
    font-size: 1.35rem;
    margin: 0;
}

.sidebar-brand p {
    color: var(--muted);
    font-size: 0.82rem;
    margin: 0.3rem 0 0;
}

.sidebar-section {
    color: var(--subtle);
    font-family: "JetBrains Mono", monospace;
    font-size: 0.7rem;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    margin: 1.1rem 0 0.5rem;
}

.sidebar-card {
    background: rgba(17, 24, 39, 0.64);
    border: 1px solid var(--line);
    border-radius: 8px;
    padding: 0.85rem;
    margin-bottom: 0.6rem;
}

.sidebar-card strong {
    color: var(--text);
    font-size: 0.9rem;
}

.sidebar-card span {
    color: var(--muted);
    display: block;
    font-size: 0.78rem;
    line-height: 1.45;
    margin-top: 0.25rem;
}

.history-item {
    border-left: 2px solid rgba(94, 234, 212, 0.5);
    padding-left: 0.7rem;
    margin-bottom: 0.75rem;
}

.history-item strong {
    color: var(--text);
    display: block;
    font-size: 0.84rem;
    line-height: 1.35;
}

.history-item span {
    color: var(--subtle);
    font-size: 0.74rem;
}

.raw-box {
    background: rgba(8, 11, 17, 0.82);
    border: 1px solid var(--line);
    border-radius: 8px;
    color: #cbd5e1;
    font-family: "JetBrains Mono", monospace;
    font-size: 0.78rem;
    line-height: 1.6;
    max-height: 24rem;
    overflow: auto;
    padding: 1rem;
    white-space: pre-wrap;
}

div[data-testid="stAlert"] {
    border-radius: 8px;
}

@media (max-width: 980px) {
    .block-container { padding: 1rem 1rem 2.5rem; }
    .topbar { align-items: flex-start; flex-direction: column; }
    .metric-grid, .stage-track, .source-grid { grid-template-columns: 1fr; }
    .stage-card { min-height: auto; }
}
</style>
        """,
        unsafe_allow_html=True,
    )


def init_state() -> None:
    defaults = {
        "results": {},
        "stage_states": {key: "waiting" for key, _, _ in PIPELINE_STAGES},
        "running": False,
        "done": False,
        "error": None,
        "history": [],
        "active_topic": "",
        "run_started_at": None,
        "run_finished_at": None,
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def escape_text(value: object) -> str:
    return html.escape(str(value or ""))


def domain_from_url(url: str) -> str:
    parsed = urlparse(url or "")
    return parsed.netloc.replace("www.", "") or "source"


def render_card(title: str, value: str, note: str = "") -> None:
    st.markdown(
        f"""
<div class="metric-card">
    <div class="metric-label">{escape_text(title)}</div>
    <div class="metric-value">{escape_text(value)}</div>
    <div class="metric-note">{escape_text(note)}</div>
</div>
        """,
        unsafe_allow_html=True,
    )


def render_stage_track() -> None:
    state = st.session_state.stage_states
    label_map = {
        "waiting": "Waiting",
        "running": "Running",
        "done": "Done",
        "skipped": "Skipped",
        "error": "Error",
    }
    cards = []

    for index, (key, name, desc) in enumerate(PIPELINE_STAGES, start=1):
        stage_state = state.get(key, "waiting")
        cards.append(
            f"""
<div class="stage-card {escape_text(stage_state)}">
    <div class="stage-index">STEP {index:02d}</div>
    <div class="stage-name">{escape_text(name)}</div>
    <div class="stage-desc">{escape_text(desc)}</div>
    <div class="stage-state"><span class="stage-dot"></span>{escape_text(label_map.get(stage_state, stage_state))}</div>
</div>
            """
        )

    st.markdown(f'<div class="stage-track">{"".join(cards)}</div>', unsafe_allow_html=True)


def set_stage(stage: str, status: str) -> None:
    st.session_state.stage_states[stage] = status


def parse_report_sections(report: str) -> dict[str, str]:
    aliases = {
        "Introduction": ["Introduction", "Overview"],
        "Key Findings": ["Key Findings", "Findings", "Main Findings"],
        "Conclusion": ["Conclusion", "Conclusions"],
        "Sources": ["Sources", "References", "Source List"],
    }
    canonical_by_alias = {
        alias.lower(): section for section, names in aliases.items() for alias in names
    }

    matches = []
    for match in re.finditer(r"(?m)^\s*(?:#+\s*)?(?:\d+[\).\s-]+)?([A-Za-z /]+)\s*:?\s*$", report or ""):
        title = match.group(1).strip()
        canonical = canonical_by_alias.get(title.lower())
        if canonical:
            matches.append((match.start(), match.end(), canonical))

    sections = {name: "" for name in aliases}
    if not matches:
        sections["Introduction"] = report or ""
        return sections

    for idx, (_, end, canonical) in enumerate(matches):
        next_start = matches[idx + 1][0] if idx + 1 < len(matches) else len(report)
        content = report[end:next_start].strip()
        sections[canonical] = content

    first_start = matches[0][0]
    if first_start > 0 and not sections["Introduction"]:
        sections["Introduction"] = report[:first_start].strip()

    return sections


def parse_bullets(block: str) -> list[str]:
    items = []
    for line in (block or "").splitlines():
        clean = re.sub(r"^\s*[-*]\s*", "", line).strip()
        if clean:
            items.append(clean)
    return items


def extract_critic_block(feedback: str, heading: str, next_headings: list[str]) -> str:
    if not feedback:
        return ""

    next_pattern = "|".join(re.escape(h) for h in next_headings)
    pattern = rf"{re.escape(heading)}:\s*(.*?)(?=\n(?:{next_pattern}):|\Z)"
    match = re.search(pattern, feedback, flags=re.I | re.S)
    return match.group(1).strip() if match else ""


def parse_critic_feedback(feedback: str) -> dict[str, object]:
    strengths = parse_bullets(
        extract_critic_block(feedback, "Strengths", ["Areas to Improve", "One line verdict"])
    )
    improvements = parse_bullets(
        extract_critic_block(feedback, "Areas to Improve", ["One line verdict", "Strengths"])
    )
    verdict_match = re.search(r"One line verdict:\s*(.+)", feedback or "", flags=re.I | re.S)
    verdict = verdict_match.group(1).strip().splitlines()[0] if verdict_match else ""

    criteria = {}
    for label in [
        "Accuracy",
        "Source Quality",
        "Citation Quality",
        "Completeness",
        "Critical Analysis",
        "Clarity",
    ]:
        match = re.search(rf"{re.escape(label)}:\s*(\d+(?:\.\d+)?)\s*/\s*10", feedback or "", flags=re.I)
        if match:
            criteria[label] = match.group(1)

    return {
        "score": extract_score(feedback or ""),
        "strengths": strengths,
        "improvements": improvements,
        "verdict": verdict,
        "criteria": criteria,
    }


def render_doc_section(title: str, content: str, fallback: str = "No content was returned for this section.") -> None:
    content = content.strip() if content else fallback
    st.markdown(
        f"""
<div class="doc-section">
    <h3>{escape_text(title)}</h3>
    <div class="content">{escape_text(content).replace(chr(10), "<br>")}</div>
</div>
        """,
        unsafe_allow_html=True,
    )


def render_source_cards(sources: list[dict]) -> None:
    if not sources:
        st.markdown(
            """
<div class="empty-state">
    <strong>No sources yet</strong>
    Source cards appear after search completes.
</div>
            """,
            unsafe_allow_html=True,
        )
        return

    cards = []
    for idx, item in enumerate(sources, start=1):
        title = item.get("title") or f"Source {idx}"
        url = item.get("url") or ""
        snippet = item.get("content") or item.get("snippet") or ""
        cards.append(
            f"""
<div class="source-card">
    <div class="source-domain">SOURCE {idx:02d} | {escape_text(domain_from_url(url))}</div>
    <div class="source-title">{escape_text(title)}</div>
    <div class="source-snippet">{escape_text(snippet[:260])}</div>
    {f'<a href="{escape_text(url)}" target="_blank" rel="noopener noreferrer">{escape_text(url)}</a>' if url else ''}
</div>
            """
        )

    st.markdown(f'<div class="source-grid">{"".join(cards)}</div>', unsafe_allow_html=True)


def render_feedback_list(title: str, items: list[str], empty: str) -> None:
    if items:
        rows = "".join(f"<li>{escape_text(item)}</li>" for item in items)
    else:
        rows = f"<li>{escape_text(empty)}</li>"

    st.markdown(
        f"""
<div class="feedback-list">
    <h4>{escape_text(title)}</h4>
    <ul>{rows}</ul>
</div>
        """,
        unsafe_allow_html=True,
    )


def copy_report_component(report: str) -> None:
    escaped = html.escape(report or "")
    st.iframe(
        f"""
<div style="font-family: Inter, system-ui, sans-serif;">
    <textarea id="report-copy" style="position:absolute;left:-9999px;">{escaped}</textarea>
    <button
        id="copy-btn"
        style="
            width:100%;
            height:44px;
            border-radius:8px;
            border:1px solid rgba(148,163,184,0.25);
            background:rgba(17,24,39,0.92);
            color:#eef4ff;
            font-weight:800;
            cursor:pointer;
        "
    >Copy Report</button>
    <script>
    const button = document.getElementById("copy-btn");
    const text = document.getElementById("report-copy").value;
    button.onclick = async () => {{
        try {{
            await navigator.clipboard.writeText(text);
            button.innerText = "Copied";
            setTimeout(() => button.innerText = "Copy Report", 1400);
        }} catch (error) {{
            const area = document.getElementById("report-copy");
            area.style.position = "fixed";
            area.style.left = "0";
            area.style.top = "0";
            area.select();
            document.execCommand("copy");
            area.style.position = "absolute";
            area.style.left = "-9999px";
            button.innerText = "Copied";
            setTimeout(() => button.innerText = "Copy Report", 1400);
        }}
    }};
    </script>
</div>
        """,
        height=54,
    )


def run_pipeline_with_live_ui(topic: str, stage_slot, detail_slot) -> None:
    st.session_state.results = {
        "topic": topic,
        "sources": [],
        "search_results": "",
        "scraped_content": "",
        "report": "",
        "feedback": "",
        "score": 0,
        "revised": False,
    }
    st.session_state.error = None
    st.session_state.done = False
    st.session_state.running = True
    st.session_state.active_topic = topic
    st.session_state.run_started_at = datetime.now()
    st.session_state.run_finished_at = None
    st.session_state.stage_states = {key: "waiting" for key, _, _ in PIPELINE_STAGES}

    try:
        set_stage("search", "running")
        with stage_slot:
            render_stage_track()
        detail_slot.info("Searching the web for reliable, recent sources...")
        search_results = get_search_results(query=topic, max_results=5)
        st.session_state.results["sources"] = search_results
        st.session_state.results["search_results"] = "\n\n".join(
            f"SOURCE {i}\n"
            f"Title: {item['title']}\n"
            f"URL: {item['url']}\n"
            f"Snippet: {item['content'][:500]}"
            for i, item in enumerate(search_results, start=1)
            if item.get("url")
        )
        set_stage("search", "done")

        set_stage("scrape", "running")
        with stage_slot:
            render_stage_track()
        detail_slot.info("Scraping the top source pages for deeper context...")
        unique_urls = list(dict.fromkeys(item["url"] for item in search_results if item.get("url")))
        scraped_sources = []

        for index, url in enumerate(unique_urls[:3], start=1):
            detail_slot.info(f"Scraping source {index} of {min(len(unique_urls), 3)}: {domain_from_url(url)}")
            try:
                content = scrape_url.invoke({"url": url})
            except Exception as exc:
                content = f"Unable to scrape this source. Error: {exc}"

            scraped_sources.append(
                f"""
SOURCE {index}
URL: {url}

CONTENT:
{content}
"""
            )

        st.session_state.results["scraped_content"] = "\n".join(scraped_sources)
        set_stage("scrape", "done")

        research_combined = (
            "SEARCH RESULTS:\n"
            f"{st.session_state.results['search_results']}\n\n"
            "DETAILED CONTENT FROM MULTIPLE SOURCES:\n"
            f"{st.session_state.results['scraped_content']}"
        )

        set_stage("writer", "running")
        with stage_slot:
            render_stage_track()
        detail_slot.info("Drafting the research report...")
        report = generate_report(topic=topic, research=research_combined)
        st.session_state.results["report"] = report
        set_stage("writer", "done")

        set_stage("critic", "running")
        with stage_slot:
            render_stage_track()
        detail_slot.info("Evaluating accuracy, citations, completeness, and clarity...")
        feedback = critic_chain.invoke({"report": report, "research": research_combined})
        score = extract_score(feedback)
        st.session_state.results["feedback"] = feedback
        st.session_state.results["score"] = score
        set_stage("critic", "done")

        if score and score < 7:
            set_stage("revision", "running")
            with stage_slot:
                render_stage_track()
            detail_slot.info("Score is below threshold. Revising the report with critic feedback...")
            revised = revise_report(
                topic=topic,
                report=report,
                feedback=feedback,
                research=research_combined,
            )
            st.session_state.results["report"] = revised
            st.session_state.results["revised"] = True
            set_stage("revision", "done")
        else:
            set_stage("revision", "skipped")

        st.session_state.running = False
        st.session_state.done = True
        st.session_state.run_finished_at = datetime.now()
        st.session_state.history.insert(
            0,
            {
                "topic": topic,
                "score": st.session_state.results.get("score", 0),
                "time": st.session_state.run_finished_at.strftime("%b %d, %I:%M %p"),
                "sources": len(st.session_state.results.get("sources", [])),
            },
        )
        st.session_state.history = st.session_state.history[:6]

        with stage_slot:
            render_stage_track()
        detail_slot.success("Research pipeline completed.")
        time.sleep(0.4)

    except Exception as exc:
        active = next(
            (key for key, status in st.session_state.stage_states.items() if status == "running"),
            None,
        )
        if active:
            set_stage(active, "error")
        st.session_state.error = str(exc)
        st.session_state.running = False
        st.session_state.done = False
        st.session_state.run_finished_at = datetime.now()
        with stage_slot:
            render_stage_track()
        detail_slot.error(f"Research failed: {exc}")


def render_sidebar() -> None:
    with st.sidebar:
        st.markdown(
            """
<div class="sidebar-brand">
    <h2>ResearchMind</h2>
    <p>Multi-agent AI research workspace</p>
</div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown('<div class="sidebar-section">New Research</div>', unsafe_allow_html=True)
        if st.button("Start New Research", use_container_width=True, type="secondary"):
            st.session_state.results = {}
            st.session_state.error = None
            st.session_state.done = False
            st.session_state.running = False
            st.session_state.stage_states = {key: "waiting" for key, _, _ in PIPELINE_STAGES}
            st.session_state.topic_input = ""
            st.rerun()

        st.markdown('<div class="sidebar-section">Research History</div>', unsafe_allow_html=True)
        if st.session_state.history:
            for item in st.session_state.history:
                st.markdown(
                    f"""
<div class="history-item">
    <strong>{escape_text(item["topic"])}</strong>
    <span>{escape_text(item["time"])} | Score {escape_text(item["score"])}/10 | {escape_text(item["sources"])} sources</span>
</div>
                    """,
                    unsafe_allow_html=True,
                )
        else:
            st.markdown(
                """
<div class="sidebar-card">
    <strong>No completed runs</strong>
    <span>Your latest research topics will appear here.</span>
</div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown('<div class="sidebar-section">Pipeline Status</div>', unsafe_allow_html=True)
        for key, name, _ in PIPELINE_STAGES:
            status = st.session_state.stage_states.get(key, "waiting")
            st.markdown(
                f"""
<div class="sidebar-card">
    <strong>{escape_text(name)}</strong>
    <span>{escape_text(status.title())}</span>
</div>
                """,
                unsafe_allow_html=True,
            )

        gemini_state = "Configured" if os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY") else "Needs API key"
        tavily_state = "Configured" if os.getenv("TAVILY_API_KEY") else "Needs API key"
        st.markdown('<div class="sidebar-section">Model/API Status</div>', unsafe_allow_html=True)
        st.markdown(
            f"""
<div class="sidebar-card">
    <strong>Gemini</strong>
    <span>{escape_text(gemini_state)} through agents.py</span>
</div>
<div class="sidebar-card">
    <strong>Tavily</strong>
    <span>{escape_text(tavily_state)} through tools.py</span>
</div>
            """,
            unsafe_allow_html=True,
        )


def render_results() -> None:
    results = st.session_state.results

    if st.session_state.error:
        st.error(st.session_state.error)

    if not results.get("report"):
        st.markdown(
            """
<div class="empty-state">
    <strong>Ready for a research run</strong>
    Enter a topic and run the pipeline to generate a structured report, quality review, and source set.
</div>
            """,
            unsafe_allow_html=True,
        )
        return

    report = results.get("report", "")
    feedback = results.get("feedback", "")
    critic = parse_critic_feedback(feedback)
    sections = parse_report_sections(report)

    st.markdown("### Final Research Report")
    action_cols = st.columns([1, 1, 4])
    with action_cols[0]:
        st.download_button(
            "Download Report",
            data=report,
            file_name=f"research_report_{int(time.time())}.md",
            mime="text/markdown",
            use_container_width=True,
        )
    with action_cols[1]:
        copy_report_component(report)

    doc_col, insight_col = st.columns([1.55, 1], gap="large")

    with doc_col:
        render_doc_section("Introduction", sections.get("Introduction", ""))
        render_doc_section("Key Findings", sections.get("Key Findings", ""))
        render_doc_section("Conclusion", sections.get("Conclusion", ""))
        render_doc_section("Sources", sections.get("Sources", ""))

        with st.expander("Full report"):
            st.markdown(report)

    with insight_col:
        st.markdown(
            f"""
<div class="quality-card">
    <div class="metric-label">Quality Score</div>
    <div class="score-ring">
        <span class="score-value">{escape_text(critic.get("score") or results.get("score") or 0)}</span>
        <span class="score-total">/10</span>
    </div>
    <div class="score-verdict">{escape_text(critic.get("verdict") or "Critic review completed.")}</div>
</div>
            """,
            unsafe_allow_html=True,
        )

        st.write("")
        render_feedback_list(
            "Strengths",
            critic.get("strengths", []),
            "The critic did not return a separate strengths list.",
        )
        render_feedback_list(
            "Areas for Improvement",
            critic.get("improvements", []),
            "The critic did not return separate improvement notes.",
        )

        criteria = critic.get("criteria", {})
        if criteria:
            st.markdown("#### Critic Breakdown")
            for label, item_score in criteria.items():
                st.progress(min(float(item_score) / 10, 1.0), text=f"{label}: {item_score}/10")

    st.markdown("### Sources")
    render_source_cards(results.get("sources", []))

    with st.expander("Pipeline raw outputs"):
        st.markdown(
            f"""
<div class="raw-box">SEARCH RESULTS

{escape_text(results.get("search_results", ""))}

SCRAPED CONTENT

{escape_text(results.get("scraped_content", ""))}

CRITIC FEEDBACK

{escape_text(feedback)}</div>
            """,
            unsafe_allow_html=True,
        )


def main() -> None:
    configure_page()
    inject_styles()
    init_state()
    render_sidebar()

    st.markdown('<div class="app-shell">', unsafe_allow_html=True)
    st.markdown(
        """
<div class="topbar">
    <div>
        <div class="eyebrow">AI Research Workspace</div>
        <h1>Research intelligence dashboard</h1>
        <p>Search, scrape, write, critique, and refine evidence-backed research from one focused dark workspace.</p>
    </div>
    <div class="status-pill">Streamlit | LangChain | Gemini | Tavily</div>
</div>
        """,
        unsafe_allow_html=True,
    )

    results = st.session_state.results
    source_count = len(results.get("sources", [])) if results else 0
    report_words = len((results.get("report", "") or "").split()) if results else 0
    score = results.get("score", 0) if results else 0
    run_state = "Running" if st.session_state.running else "Complete" if st.session_state.done else "Idle"

    metric_cols = st.columns(4)
    with metric_cols[0]:
        render_card("Run State", run_state, st.session_state.active_topic or "Awaiting topic")
    with metric_cols[1]:
        render_card("Sources", str(source_count), "Top search results")
    with metric_cols[2]:
        render_card("Report Words", str(report_words), "Final draft length")
    with metric_cols[3]:
        render_card("Critic Score", f"{score}/10", "Quality review")

    input_col, pipeline_col = st.columns([1.05, 1], gap="large")

    with input_col:
        st.markdown(
            """
<div class="workspace-card">
    <div class="workspace-title">New Research</div>
    <div class="workspace-caption">Enter a research topic and run the existing multi-agent pipeline.</div>
</div>
            """,
            unsafe_allow_html=True,
        )
        topic = st.text_area(
            "Research topic",
            key="topic_input",
            placeholder="Example: recent progress in practical quantum error correction",
            height=112,
            disabled=st.session_state.running,
        )
        run_clicked = st.button(
            "Run Research Pipeline",
            type="primary",
            use_container_width=True,
            disabled=st.session_state.running,
        )

    with pipeline_col:
        st.markdown("### Pipeline")
        stage_slot = st.empty()
        detail_slot = st.empty()
        with stage_slot:
            render_stage_track()
        if not st.session_state.running and not st.session_state.done:
            detail_slot.info("Pipeline is idle.")
        elif st.session_state.done:
            detail_slot.success("Latest run completed.")

    if run_clicked:
        cleaned_topic = topic.strip()
        if not cleaned_topic:
            st.warning("Enter a research topic before running the pipeline.")
        else:
            run_pipeline_with_live_ui(cleaned_topic, stage_slot, detail_slot)
            st.rerun()

    st.markdown("---")
    render_results()
    st.markdown("</div>", unsafe_allow_html=True)
