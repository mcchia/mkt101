"""Shared Streamlit styling system.

One place to keep the premium, calm, tea-inspired visual language:
- CSS variables for the palette
- Serif headings, humanist sans body
- Softer container borders, cleaner forms, quieter alerts
- Reusable Python helpers so every page composes the same way

Every page should start with `apply_theme()` and use `page_header()` + the
shared helpers instead of raw st.title / st.caption / st.subheader so the
look stays consistent.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator, Literal

import streamlit as st

TONE = Literal["neutral", "success", "warning", "danger", "info"]


_CSS = """
<style>
:root {
    --tea-bg:        #FAF8F3;
    --tea-surface:   #FFFFFF;
    --tea-sidebar:   #F2EEE5;
    --tea-ink:       #1E2A24;
    --tea-ink-soft:  #3E4A42;
    --tea-muted:     #6B675E;
    --tea-line:      #EAE6DC;
    --tea-line-soft: #F2EEE5;
    --tea-primary:   #2F4A3A;
    --tea-primary-hover: #24382C;
    --tea-accent:    #E8DCC4;
    --tea-success:   #5B7A5A;
    --tea-warning:   #B07D3B;
    --tea-danger:    #9E4B3C;
    --tea-radius:    10px;
    --tea-radius-sm: 6px;
    --tea-serif:     "Iowan Old Style", "Palatino Linotype", "Palatino", "Georgia", "Times New Roman", serif;
    --tea-sans:      -apple-system, BlinkMacSystemFont, "Inter", "Segoe UI", "Helvetica Neue", Arial, sans-serif;
}

/* ---- Base typography --------------------------------------------------- */
html, body, [class*="st-"], [data-testid="stAppViewContainer"] {
    font-family: var(--tea-sans);
    color: var(--tea-ink);
}
h1, h2, h3, h4, .tea-title, .tea-section-title {
    font-family: var(--tea-serif);
    letter-spacing: -0.005em;
    color: var(--tea-ink);
    font-weight: 600;
}
p, li, label, .stMarkdown, [data-testid="stCaption"] {
    line-height: 1.55;
}
a, a:visited {
    color: var(--tea-primary);
    text-decoration-thickness: 1px;
    text-underline-offset: 2px;
}

/* ---- App container ---------------------------------------------------- */
[data-testid="stAppViewContainer"] {
    background: var(--tea-bg);
}
.block-container {
    padding-top: 2.25rem;
    padding-bottom: 4rem;
    max-width: 1120px;
}

/* Reduce the default top header noise, keep a quiet hairline. */
[data-testid="stHeader"] {
    background: transparent;
    height: auto;
}
[data-testid="stHeader"]::after {
    content: "";
    display: block;
    height: 1px;
    background: var(--tea-line);
    opacity: 0.6;
}

/* ---- Sidebar ---------------------------------------------------------- */
[data-testid="stSidebar"] {
    background: var(--tea-sidebar);
    border-right: 1px solid var(--tea-line);
}
[data-testid="stSidebar"] * {
    font-family: var(--tea-sans);
}
[data-testid="stSidebarNav"] a, [data-testid="stSidebarNavLink"] {
    border-radius: var(--tea-radius-sm);
}

/* ---- Buttons ---------------------------------------------------------- */
.stButton > button, .stFormSubmitButton > button, [data-testid="stDownloadButton"] > button {
    border-radius: var(--tea-radius-sm);
    border: 1px solid var(--tea-line);
    background: var(--tea-surface);
    color: var(--tea-ink);
    font-weight: 500;
    padding: 0.5rem 0.95rem;
    transition: all 0.12s ease;
    box-shadow: none;
}
.stButton > button:hover, .stFormSubmitButton > button:hover {
    border-color: var(--tea-ink-soft);
    color: var(--tea-ink);
    background: var(--tea-line-soft);
}
.stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primary"] {
    background: var(--tea-primary);
    border-color: var(--tea-primary);
    color: #FAF8F3;
}
.stButton > button[kind="primary"]:hover, .stFormSubmitButton > button[kind="primary"]:hover {
    background: var(--tea-primary-hover);
    border-color: var(--tea-primary-hover);
    color: #FFFFFF;
}
.stButton > button:focus, .stFormSubmitButton > button:focus {
    box-shadow: 0 0 0 2px rgba(47, 74, 58, 0.15);
    outline: none;
}

/* ---- Form fields ------------------------------------------------------ */
.stTextInput input, .stTextArea textarea, .stNumberInput input, .stDateInput input,
.stTimeInput input, .stSelectbox [data-baseweb="select"] > div,
.stMultiSelect [data-baseweb="select"] > div {
    background: var(--tea-surface) !important;
    border-radius: var(--tea-radius-sm) !important;
    border: 1px solid var(--tea-line) !important;
    color: var(--tea-ink) !important;
    box-shadow: none !important;
}
.stTextInput input:focus, .stTextArea textarea:focus, .stNumberInput input:focus {
    border-color: var(--tea-primary) !important;
    box-shadow: 0 0 0 2px rgba(47, 74, 58, 0.12) !important;
}
label, .stTextInput label, .stTextArea label, .stSelectbox label,
.stMultiSelect label, .stNumberInput label, .stRadio label,
.stCheckbox label {
    color: var(--tea-ink-soft) !important;
    font-weight: 500 !important;
    font-size: 0.88rem !important;
}

/* ---- Tabs ------------------------------------------------------------- */
[data-baseweb="tab-list"] {
    border-bottom: 1px solid var(--tea-line) !important;
    gap: 0.25rem;
}
[data-baseweb="tab"] {
    background: transparent !important;
    color: var(--tea-muted) !important;
    font-weight: 500 !important;
    padding: 0.55rem 0.85rem !important;
    border-radius: var(--tea-radius-sm) var(--tea-radius-sm) 0 0 !important;
}
[data-baseweb="tab"][aria-selected="true"] {
    color: var(--tea-ink) !important;
    border-bottom: 2px solid var(--tea-primary) !important;
}

/* ---- Containers, cards, expanders ------------------------------------ */
[data-testid="stVerticalBlockBorderWrapper"] {
    border: 1px solid var(--tea-line) !important;
    border-radius: var(--tea-radius) !important;
    background: var(--tea-surface);
    box-shadow: 0 1px 0 rgba(30, 42, 36, 0.02);
}
[data-testid="stExpander"] {
    border: 1px solid var(--tea-line) !important;
    border-radius: var(--tea-radius) !important;
    background: var(--tea-surface);
    box-shadow: none;
}
[data-testid="stExpander"] summary {
    font-weight: 500;
    color: var(--tea-ink);
}
[data-testid="stExpander"] summary:hover {
    color: var(--tea-primary);
}

/* ---- Alerts ----------------------------------------------------------- */
[data-testid="stAlert"] {
    border-radius: var(--tea-radius);
    border: 1px solid var(--tea-line);
    background: var(--tea-surface);
    padding: 0.85rem 1rem;
    box-shadow: none;
}
[data-testid="stAlert"] [data-testid="stMarkdownContainer"] {
    color: var(--tea-ink);
}
/* Calm left-edge accent by severity, no loud fills. */
div[data-testid="stAlert"]:has(svg[data-testid="stAlertIconInfo"]) {
    border-left: 3px solid var(--tea-primary);
}
div[data-testid="stAlert"]:has(svg[data-testid="stAlertIconSuccess"]) {
    border-left: 3px solid var(--tea-success);
}
div[data-testid="stAlert"]:has(svg[data-testid="stAlertIconWarning"]) {
    border-left: 3px solid var(--tea-warning);
}
div[data-testid="stAlert"]:has(svg[data-testid="stAlertIconError"]) {
    border-left: 3px solid var(--tea-danger);
}

/* ---- Metrics / KPIs --------------------------------------------------- */
[data-testid="stMetric"] {
    background: var(--tea-surface);
    border: 1px solid var(--tea-line);
    border-radius: var(--tea-radius);
    padding: 0.85rem 1rem;
}
[data-testid="stMetricLabel"] {
    color: var(--tea-muted) !important;
    font-weight: 500 !important;
    font-size: 0.8rem !important;
    letter-spacing: 0.01em;
    text-transform: uppercase;
}
[data-testid="stMetricValue"] {
    font-family: var(--tea-serif);
    color: var(--tea-ink);
    font-weight: 600;
}

/* ---- Tables / DataFrames --------------------------------------------- */
[data-testid="stDataFrame"] {
    border: 1px solid var(--tea-line);
    border-radius: var(--tea-radius);
    overflow: hidden;
}
[data-testid="stDataFrame"] thead tr th {
    background: var(--tea-line-soft) !important;
    color: var(--tea-ink-soft) !important;
    font-weight: 500 !important;
    border-bottom: 1px solid var(--tea-line) !important;
}
[data-testid="stDataFrame"] tbody tr td {
    border-bottom: 1px solid var(--tea-line-soft) !important;
}

/* ---- Chat bubbles ----------------------------------------------------- */
[data-testid="stChatMessage"] {
    background: var(--tea-surface);
    border: 1px solid var(--tea-line);
    border-radius: var(--tea-radius);
    padding: 0.9rem 1.05rem;
    box-shadow: 0 1px 0 rgba(30, 42, 36, 0.02);
}
[data-testid="stChatInput"] textarea {
    border-radius: var(--tea-radius) !important;
    border: 1px solid var(--tea-line) !important;
    background: var(--tea-surface) !important;
}

/* ---- Dividers --------------------------------------------------------- */
hr, [data-testid="stDivider"] {
    border: none !important;
    border-top: 1px solid var(--tea-line) !important;
    margin: 1.5rem 0 !important;
    opacity: 0.9;
}

/* ---- Custom helper components ---------------------------------------- */
.tea-page-header {
    margin-bottom: 1.5rem;
    padding-bottom: 1.1rem;
    border-bottom: 1px solid var(--tea-line);
}
.tea-eyebrow {
    text-transform: uppercase;
    letter-spacing: 0.12em;
    font-size: 0.72rem;
    font-weight: 600;
    color: var(--tea-primary);
    margin-bottom: 0.35rem;
    font-family: var(--tea-sans);
}
.tea-page-title {
    font-family: var(--tea-serif);
    font-size: 2rem;
    line-height: 1.15;
    margin: 0 0 0.4rem 0;
    color: var(--tea-ink);
    font-weight: 600;
}
.tea-page-subtitle {
    color: var(--tea-muted);
    font-size: 0.98rem;
    margin: 0;
    max-width: 68ch;
}
.tea-section {
    margin: 2rem 0 0.9rem 0;
}
.tea-section-title {
    font-size: 1.08rem;
    color: var(--tea-ink);
    margin: 0;
}
.tea-section-subtitle {
    color: var(--tea-muted);
    font-size: 0.88rem;
    margin: 0.1rem 0 0 0;
}
.tea-badge {
    display: inline-flex;
    align-items: center;
    padding: 0.15rem 0.55rem;
    border-radius: 999px;
    font-size: 0.75rem;
    font-weight: 500;
    letter-spacing: 0.01em;
    border: 1px solid var(--tea-line);
    background: var(--tea-surface);
    color: var(--tea-ink-soft);
    font-family: var(--tea-sans);
}
.tea-badge--success { color: var(--tea-success); border-color: rgba(91, 122, 90, 0.30); background: rgba(91, 122, 90, 0.08); }
.tea-badge--warning { color: var(--tea-warning); border-color: rgba(176, 125, 59, 0.30); background: rgba(176, 125, 59, 0.08); }
.tea-badge--danger  { color: var(--tea-danger);  border-color: rgba(158, 75, 60, 0.30);  background: rgba(158, 75, 60, 0.08); }
.tea-badge--info    { color: var(--tea-primary); border-color: rgba(47, 74, 58, 0.28);   background: rgba(47, 74, 58, 0.06); }

.tea-empty {
    border: 1px dashed var(--tea-line);
    border-radius: var(--tea-radius);
    padding: 2rem 1.5rem;
    text-align: center;
    color: var(--tea-muted);
    background: transparent;
}
.tea-empty-title {
    font-family: var(--tea-serif);
    color: var(--tea-ink);
    font-size: 1.05rem;
    margin-bottom: 0.25rem;
}

.tea-kv {
    display: grid;
    grid-template-columns: max-content 1fr;
    gap: 0.2rem 0.9rem;
    margin: 0.25rem 0 0.5rem 0;
}
.tea-kv dt {
    color: var(--tea-muted);
    font-size: 0.85rem;
    font-weight: 500;
}
.tea-kv dd {
    color: var(--tea-ink);
    margin: 0;
}

.tea-quote {
    border-left: 3px solid var(--tea-accent);
    background: rgba(232, 220, 196, 0.18);
    padding: 0.6rem 0.9rem;
    border-radius: 0 var(--tea-radius-sm) var(--tea-radius-sm) 0;
    color: var(--tea-ink-soft);
    font-style: italic;
}

/* Reduce default Streamlit crowding between widgets. */
.element-container { margin-bottom: 0.35rem; }
</style>
"""


def apply_theme() -> None:
    """Inject the CSS theme. Safe to call once per page render."""
    if st.session_state.get("_tea_theme_applied"):
        return
    st.markdown(_CSS, unsafe_allow_html=True)
    st.session_state["_tea_theme_applied"] = True


def page_header(title: str, subtitle: str | None = None, eyebrow: str | None = None) -> None:
    """Consistent page header: small eyebrow label, serif title, muted subtitle."""
    bits: list[str] = ['<div class="tea-page-header">']
    if eyebrow:
        bits.append(f'<div class="tea-eyebrow">{_esc(eyebrow)}</div>')
    bits.append(f'<h1 class="tea-page-title">{_esc(title)}</h1>')
    if subtitle:
        bits.append(f'<p class="tea-page-subtitle">{_esc(subtitle)}</p>')
    bits.append("</div>")
    st.markdown("".join(bits), unsafe_allow_html=True)


def section(title: str, subtitle: str | None = None) -> None:
    """Section header used between groups of controls."""
    bits = [
        '<div class="tea-section">',
        f'<h3 class="tea-section-title">{_esc(title)}</h3>',
    ]
    if subtitle:
        bits.append(f'<p class="tea-section-subtitle">{_esc(subtitle)}</p>')
    bits.append("</div>")
    st.markdown("".join(bits), unsafe_allow_html=True)


@contextmanager
def card() -> Iterator[None]:
    """Soft bordered container. Prefer this over raw st.container(border=True)
    so every card shares the same theme treatment."""
    with st.container(border=True):
        yield


def badge(label: str, tone: TONE = "neutral") -> None:
    """Render a quiet status pill inline."""
    cls = "tea-badge"
    if tone and tone != "neutral":
        cls += f" tea-badge--{tone}"
    st.markdown(f'<span class="{cls}">{_esc(label)}</span>', unsafe_allow_html=True)


def badge_html(label: str, tone: TONE = "neutral") -> str:
    """Return a badge as HTML (for inline composition inside markdown)."""
    cls = "tea-badge"
    if tone and tone != "neutral":
        cls += f" tea-badge--{tone}"
    return f'<span class="{cls}">{_esc(label)}</span>'


def empty_state(title: str, body: str | None = None) -> None:
    bits = ['<div class="tea-empty">', f'<div class="tea-empty-title">{_esc(title)}</div>']
    if body:
        bits.append(f"<div>{_esc(body)}</div>")
    bits.append("</div>")
    st.markdown("".join(bits), unsafe_allow_html=True)


def kv_list(items: list[tuple[str, str]]) -> None:
    """Compact label/value list for key-value summaries."""
    if not items:
        return
    rows = "".join(f"<dt>{_esc(k)}</dt><dd>{_esc(v)}</dd>" for k, v in items if v)
    if rows:
        st.markdown(f'<dl class="tea-kv">{rows}</dl>', unsafe_allow_html=True)


def quote(text: str) -> None:
    st.markdown(f'<blockquote class="tea-quote">{_esc(text)}</blockquote>', unsafe_allow_html=True)


def tone_for_score(score: int) -> TONE:
    """Map a 0-100 risk score to a calm tone."""
    if score < 20:
        return "success"
    if score < 50:
        return "warning"
    return "danger"


def _esc(text: object) -> str:
    s = "" if text is None else str(text)
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
