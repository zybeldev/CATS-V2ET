from __future__ import annotations

from html import escape
import json
import os
import re
from pathlib import Path
import subprocess
import sys
from typing import Any, Iterable
from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import streamlit as st
from sqlalchemy import text

from cats.configuration import get_settings
from cats.database import create_engine_from_settings
from cats.ui import (
    CatsUiReadModel,
    STAGE_TABLES,
    build_paper_command,
    normalize_symbol,
    stage_local_evidence,
    validate_evidence_reference,
    describe_launcher_failure,
    main_loop_is_running,
    probe_qwen_health,
    read_main_loop_status,
    start_main_loop,
    stop_main_loop,
    tail_runtime_log,
)


st.set_page_config(
    page_title="CATS V2ET — Autonomous Trading System",
    page_icon="🐈",
    layout="wide",
)

# Report-style observability presentation: one material fact per line rather than
# wide metric grids. This is intentionally a presentation-only layer.
st.markdown(
    """
    <style>
    .block-container { padding-top: 1.25rem !important; }
    h1 { font-size: 1.88rem !important; line-height: 1.18 !important; margin-top: 0 !important; margin-bottom: 0.35rem !important; overflow: visible !important; }
    h2 { font-size: 1.35rem !important; line-height: 1.2 !important; margin-top: 0.55rem !important; }
    h3 { font-size: 1.08rem !important; line-height: 1.25 !important; }

    .cats-report-card {
        background: #f7f7f8;
        border: 1px solid #e3e5e8;
        border-radius: 14px;
        padding: 0.95rem 1.05rem 1.0rem 1.05rem;
        margin: 0.35rem 0 1.15rem 0;
    }
    .cats-report-title {
        font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace;
        font-size: 0.98rem;
        font-weight: 700;
        margin: 0;
    }
    .cats-report-subtitle {
        margin: 0.16rem 0 0 0;
        font-size: 0.82rem;
        font-weight: 600;
        color: #667085;
    }
    .cats-market-chart {
        margin-top: 0.85rem;
        padding: 0.7rem 0.7rem 0.55rem 0.7rem;
        background: #ffffff;
        border: 1px solid #e3e5e8;
        border-radius: 9px;
    }
    .cats-market-chart-title {
        margin: 0 0 0.45rem 0;
        font-size: 0.82rem;
        font-weight: 700;
        color: #40454d;
    }
    .cats-market-chart svg {
        display: block;
        width: 100%;
        height: auto;
    }
    .cats-signal-strip {
        display: flex;
        flex-wrap: wrap;
        gap: 0.35rem;
        margin-top: 0.45rem;
    }
    .cats-signal-chip {
        padding: 0.18rem 0.42rem;
        border: 1px solid #d8dde4;
        border-radius: 5px;
        background: #f8fafc;
        font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace;
        font-size: 0.72rem;
        color: #40454d;
    }
    .cats-report-rule {
        width: min(100%, 42rem);
        border-top: 1px solid #5f6368;
        margin: 0.35rem 0 0.8rem 0;
    }
    .cats-report-row {
        display: grid;
        grid-template-columns: 11.5rem minmax(0, 1fr);
        column-gap: 1rem;
        align-items: baseline;
        margin: 0.08rem 0;
        font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace;
        font-size: 0.92rem;
        line-height: 1.5;
    }
    .cats-report-label {
        color: #202124;
        white-space: normal;
        overflow-wrap: anywhere;
    }
    .cats-report-value {
        color: #111827;
        font-weight: 500;
        overflow-wrap: anywhere;
    }
    .cats-live-time {
        display: inline-block;
        background: transparent;
        border: 1px solid transparent;
        border-radius: 5px;
        padding: 0.02rem 0.34rem;
        font-weight: 700;
        animation: cats-refresh-pulse 5s ease-out 1 forwards;
    }
    @keyframes cats-refresh-pulse {
        0% { background: #fff1a8; border-color: #e7cf63; }
        90% { background: #fff1a8; border-color: #e7cf63; }
        100% { background: transparent; border-color: transparent; }
    }
    .cats-report-subheading {
        margin-top: 0.95rem;
        margin-bottom: 0.25rem;
        font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace;
        font-size: 0.92rem;
        font-weight: 700;
    }
    .cats-report-narrative {
        margin: 0.2rem 0 0 0;
        padding: 0.6rem 0.75rem;
        font-size: 0.96rem;
        line-height: 1.6;
        color: #30343b;
        background: #ffffff;
        border: 1px solid #e3e5e8;
        border-radius: 8px;
        overflow-wrap: anywhere;
    }
    .cats-news-card .cats-report-subheading {
        display: inline-block;
        margin-top: 0.9rem;
        padding: 0.28rem 0.55rem;
        background: #e8eef7;
        border: 1px solid #d8e1ef;
        border-radius: 6px;
    }
    .cats-reasoning-panel {
        margin-top: 0.85rem;
        padding: 0.8rem 0.9rem 0.7rem 0.9rem;
        background: #ffffff;
        border: 1px solid #dde2e7;
        border-radius: 10px;
    }
    .cats-reasoning-panel .cats-report-subheading {
        margin-top: 0;
    }
    .cats-assessment-section {
        margin-top: 0.8rem;
        padding: 0.55rem 0.7rem 0.45rem 0.7rem;
        background: #ffffff;
        border: 1px solid #e3e5e8;
        border-radius: 8px;
    }
    .cats-assessment-section-title {
        display: inline-block;
        margin: 0 0 0.28rem 0;
        padding: 0.2rem 0.45rem;
        background: #eef3f8;
        border-radius: 5px;
        font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace;
        font-size: 0.90rem;
        font-weight: 700;
        color: #30343b;
    }
    .cats-assessment-bullets {
        margin: 0.15rem 0 0.2rem 1.15rem;
        padding: 0;
        color: #30343b;
        font-size: 0.96rem;
        line-height: 1.55;
    }
    .cats-assessment-bullets li {
        margin: 0.24rem 0;
        padding-left: 0.12rem;
    }
    .cats-report-note {
        margin-top: 0.7rem;
        font-size: 0.82rem;
        color: #777c85;
        line-height: 1.45;
    }
    .cats-report-chain .cats-report-row {
        grid-template-columns: 10rem minmax(0, 1fr);
    }
    .cats-components .cats-report-row {
        grid-template-columns: 3.0rem minmax(0, 1fr);
        column-gap: 0.55rem;
        font-size: 0.78rem;
        line-height: 1.35;
        margin: 0.22rem 0;
    }
    .cats-components .cats-report-rule {
        width: 100%;
    }
    .cats-components .cats-report-note {
        font-size: 0.74rem;
    }
    .cats-sidebar-system .cats-report-row {
        grid-template-columns: 6.6rem minmax(0, 1fr);
        column-gap: 0.45rem;
        font-size: 0.78rem;
        line-height: 1.35;
    }
    .cats-sidebar-system .cats-report-rule {
        width: 100%;
    }
    .cats-sidebar-system .cats-report-note {
        font-size: 0.74rem;
    }
    @media (max-width: 700px) {
        .cats-report-row,
        .cats-report-chain .cats-report-row {
            grid-template-columns: 1fr;
            row-gap: 0.05rem;
            margin-bottom: 0.35rem;
        }
        .cats-report-label { font-weight: 700; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def short(value: Any, n: int = 12) -> str:
    if value is None:
        return "—"
    text = str(value)
    return text if len(text) <= n else text[:n] + "…"


def display_status(value: Any) -> str:
    return "—" if value is None else str(value)


def startup_recovery_label(payload: Any) -> str:
    if not isinstance(payload, dict):
        return "—"
    status = str(payload.get("status") or "—").upper()
    recovered = int(payload.get("recovered_flow_count") or 0)
    unresolved = int(payload.get("unresolved_flow_count") or 0)
    if status == "COMPLETED":
        return f"COMPLETED · {recovered} flow(s)"
    if status == "BLOCKED":
        return f"BLOCKED · {unresolved} unresolved"
    if status == "CLEAR":
        return "CLEAR"
    return status


def run_startup_recovery(project_root: Path) -> tuple[dict[str, Any], str, int]:
    """Run deterministic PAPER recovery without requiring the reasoning model.

    Recovery is deliberately separated from normal TAA/PMA startup. The helper
    process depends on PostgreSQL + Alpaca PAPER only and emits one tagged JSON
    summary that the Streamlit operator layer can display even when Qwen is down.
    """
    completed = subprocess.run(
        [sys.executable, str(project_root / "scripts" / "cats_startup_recovery.py")],
        cwd=project_root,
        env=os.environ.copy(),
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )
    output = (completed.stdout or "") + ("\n" + completed.stderr if completed.stderr else "")
    payload: dict[str, Any] = {
        "status": "BLOCKED",
        "checked_flow_count": 0,
        "recovered_flow_count": 0,
        "unresolved_flow_count": 0,
        "flows": [],
        "detail": "Startup recovery did not return a structured result.",
    }
    prefix = "CATS_STARTUP_RECOVERY_JSON="
    for line in (completed.stdout or "").splitlines():
        if line.startswith(prefix):
            try:
                candidate = json.loads(line[len(prefix):])
            except json.JSONDecodeError:
                continue
            if isinstance(candidate, dict):
                payload = candidate
    if completed.returncode != 0 and str(payload.get("status") or "").upper() != "BLOCKED":
        payload = {
            **payload,
            "status": "BLOCKED",
            "detail": payload.get("detail") or f"Startup recovery process exited with code {completed.returncode}.",
        }
    return payload, output[-12000:], completed.returncode


def number(value: Any, decimals: int = 4) -> str:
    if value is None:
        return "—"
    return f"{float(value):,.{decimals}f}"


def usd(value: Any) -> str:
    if value is None:
        return "—"
    value = float(value)
    sign = "-" if value < 0 else ""
    return f"{sign}${abs(value):,.2f}"


def pct(value: Any) -> str:
    if value is None:
        return "—"
    return f"{float(value) * 100:.2f}%"


def approx_usd(value: Any) -> str:
    amount = usd(value)
    return "" if amount == "—" else f"≈ {amount}"


EVALUATION_MODE = "EVALUATION / MONITORING"
PAPER_EXECUTION_MODE = "PAPER EXECUTION"
OPERATING_MODES = [EVALUATION_MODE, PAPER_EXECUTION_MODE]
MANUAL_TRIGGER_ONLY = "MANUAL_TRIGGER_ONLY"
AUTO_PAPER_EXECUTION = "AUTO_PAPER_EXECUTION"
SYS_PROFILE_NORMAL = "NORMAL"
SYS_PROFILE_AGGRESSIVE_PAPER_TEST = "AGGRESSIVE_PAPER_TEST"


def active_sys_profile() -> str:
    return os.getenv("CATS_SYS_PROFILE", SYS_PROFILE_NORMAL).strip().upper() or SYS_PROFILE_NORMAL


def sys_profile_display(profile: str) -> str:
    if profile == SYS_PROFILE_AGGRESSIVE_PAPER_TEST:
        return "AGGRESSIVE — PAPER TEST"
    if profile == SYS_PROFILE_NORMAL:
        return "NORMAL"
    return profile.replace("_", " ")


TECH_EQUITIES: dict[str, str] = {
    "AAPL": "Apple",
    "NVDA": "NVIDIA",
    "MSFT": "Microsoft",
    "GOOGL": "Alphabet",
    "AMZN": "Amazon",
    "META": "Meta Platforms",
    "AVGO": "Broadcom",
    "AMD": "AMD",
    "ORCL": "Oracle",
    "CRM": "Salesforce",
    "ADBE": "Adobe",
    "INTC": "Intel",
    "QCOM": "Qualcomm",
    "NFLX": "Netflix",
    "TSLA": "Tesla",
}


def instrument_name(symbol: Any) -> str:
    text = "" if symbol is None else str(symbol).strip().upper()
    return TECH_EQUITIES.get(text, text or "—")


def instrument_label(symbol: Any) -> str:
    text = "" if symbol is None else str(symbol).strip().upper()
    if not text:
        return "—"
    name = TECH_EQUITIES.get(text)
    return f"{text} ({name})" if name else text


def operator_timezone():
    name = (os.getenv("CATS_UI_TIMEZONE") or "America/Phoenix").strip()
    try:
        return ZoneInfo(name)
    except ZoneInfoNotFoundError:
        return timezone.utc


def operator_timestamp(value: Any) -> str:
    """Format persisted UTC/TIMESTAMPTZ values for the operator UI only."""
    if value in {None, "", "—"}:
        return "—"
    if isinstance(value, datetime):
        dt = value
    else:
        text_value = str(value).strip()
        try:
            dt = datetime.fromisoformat(text_value.replace("Z", "+00:00"))
        except ValueError:
            return text_value
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    local = dt.astimezone(operator_timezone())
    return f"{local.strftime('%b')} {local.day}, {local.year}   {local.strftime('%I:%M:%S %p %Z')}"


def recorded_operator_timestamp(value: Any) -> str:
    """Show an explicit historical gap instead of an ambiguous dash."""
    if value in {None, "", "—"}:
        return "NOT RECORDED"
    return operator_timestamp(value)


def _timestamp_value(row: dict[str, Any] | None, *keys: str) -> Any:
    if not row:
        return None
    for key in keys:
        value = row.get(key)
        if value not in {None, ""}:
            return value
    return None


def _as_utc_datetime(value: Any) -> datetime | None:
    if value in {None, "", "—"}:
        return None
    if isinstance(value, datetime):
        dt = value
    else:
        try:
            dt = datetime.fromisoformat(str(value).strip().replace("Z", "+00:00"))
        except ValueError:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _related_row(
    model: Any,
    table_name: str,
    where_column: str,
    where_value: Any,
    *,
    order_candidates: tuple[str, ...] = (),
    descending: bool = False,
) -> dict[str, Any]:
    """Read one related persistence row without changing CATS state."""
    if where_value in {None, ""} or not model.table_exists(table_name):
        return {}
    columns = set(model.columns(table_name))
    if where_column not in columns:
        return {}
    order_column = next((name for name in order_candidates if name in columns), None)
    quote = model.engine.dialect.identifier_preparer.quote
    order_sql = ""
    if order_column:
        direction = "DESC" if descending else "ASC"
        order_sql = f" ORDER BY {quote(order_column)} {direction}"
    sql = text(
        f"SELECT * FROM {quote(table_name)} "
        f"WHERE {quote(where_column)} = :value{order_sql} LIMIT 1"
    )
    with model.engine.connect() as conn:
        row = conn.execute(sql, {"value": str(where_value)}).mappings().first()
    return dict(row) if row else {}


def _timeline_rows(events: list[tuple[str, Any]]) -> list[tuple[str, Any, str | None]]:
    """Display events in CATS causal order while preserving persisted timestamps exactly.

    The caller supplies the canonical authority/execution sequence. This avoids visually
    impossible reordering when several persisted events share the same displayed second
    or when one historical event has no dedicated timestamp.
    """
    return [
        (label, recorded_operator_timestamp(raw_value), None)
        for label, raw_value in events
    ]


def _timeline_has_recorded_regression(events: list[tuple[str, Any]]) -> bool:
    """Return True only when persisted event time moves backward by more than display precision."""
    previous: datetime | None = None
    for _, raw_value in events:
        current = _as_utc_datetime(raw_value)
        if current is None:
            continue
        # The operator UI displays seconds, so microsecond differences inside the same
        # displayed second are not treated as a chronology failure.
        current = current.replace(microsecond=0)
        if previous is not None and current < previous:
            return True
        previous = current
    return False


def _operator_history_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Presentation-only copy of flow rows with persisted timestamps rendered in operator local time."""
    rendered: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        for key, value in list(item.items()):
            lowered = str(key).lower()
            if value not in {None, ""} and (lowered.endswith("_at") or "timestamp" in lowered):
                item[key] = operator_timestamp(value)
        rendered.append(item)
    return rendered


def signal_direction(value: Any) -> str:
    if value is None:
        return "—"
    numeric = float(value)
    if numeric > 0:
        return "POSITIVE"
    if numeric < 0:
        return "NEGATIVE"
    return "FLAT"


def relative_state(left: Any, right: Any, *, above: str = "ABOVE", below: str = "BELOW") -> str:
    if left is None or right is None:
        return "—"
    left_value = float(left)
    right_value = float(right)
    if left_value > right_value:
        return above
    if left_value < right_value:
        return below
    return "AT"




def _rolling_sma(values: list[float], window: int) -> list[float | None]:
    result: list[float | None] = []
    for index in range(len(values)):
        if index + 1 < window:
            result.append(None)
        else:
            sample = values[index + 1 - window : index + 1]
            result.append(sum(sample) / window)
    return result


def candlestick_signal_chart_html(row: dict[str, Any]) -> str:
    """Presentation-only candlestick view built from the same daily bars TSS used."""
    source = row.get("price_bars") or []
    bars: list[dict[str, Any]] = []
    for item in source[-30:]:
        try:
            bars.append(
                {
                    "timestamp": str(item.get("timestamp") or ""),
                    "open": float(item["open"]),
                    "high": float(item["high"]),
                    "low": float(item["low"]),
                    "close": float(item["close"]),
                }
            )
        except (KeyError, TypeError, ValueError):
            continue

    if len(bars) < 2:
        return (
            '<div class="cats-market-chart">'
            '<div class="cats-market-chart-title">Candlestick Market View</div>'
            '<div class="cats-report-note">OHLC history is not available for this observation.</div>'
            '</div>'
        )

    width = 900.0
    height = 300.0
    left = 54.0
    right = 18.0
    top = 18.0
    bottom = 42.0
    plot_width = width - left - right
    plot_height = height - top - bottom

    low_price = min(item["low"] for item in bars)
    high_price = max(item["high"] for item in bars)
    span = max(high_price - low_price, max(abs(high_price), 1.0) * 0.001)
    low_price -= span * 0.04
    high_price += span * 0.04
    span = high_price - low_price

    def y(value: float) -> float:
        return top + (high_price - value) / span * plot_height

    step = plot_width / len(bars)
    body_width = max(3.0, min(14.0, step * 0.58))
    svg: list[str] = [
        f'<svg viewBox="0 0 {width:.0f} {height:.0f}" role="img" '
        'aria-label="Daily candlestick chart with TSS short and long moving averages">'
    ]

    for fraction in (0.0, 0.5, 1.0):
        price = high_price - fraction * span
        ypos = top + fraction * plot_height
        svg.append(
            f'<line x1="{left:.1f}" y1="{ypos:.1f}" x2="{width-right:.1f}" y2="{ypos:.1f}" '
            'stroke="#e5e7eb" stroke-width="1" />'
        )
        svg.append(
            f'<text x="{left-7:.1f}" y="{ypos+4:.1f}" text-anchor="end" '
            'font-size="11" fill="#667085">'
            f'${price:,.2f}</text>'
        )

    for index, item in enumerate(bars):
        xpos = left + step * (index + 0.5)
        open_y = y(item["open"])
        close_y = y(item["close"])
        high_y = y(item["high"])
        low_y = y(item["low"])
        rising = item["close"] >= item["open"]
        color = "#16834b" if rising else "#c63f3f"
        body_y = min(open_y, close_y)
        body_height = max(1.2, abs(close_y - open_y))
        svg.append(
            f'<line x1="{xpos:.2f}" y1="{high_y:.2f}" x2="{xpos:.2f}" y2="{low_y:.2f}" '
            f'stroke="{color}" stroke-width="1.2" />'
        )
        svg.append(
            f'<rect x="{xpos-body_width/2:.2f}" y="{body_y:.2f}" width="{body_width:.2f}" '
            f'height="{body_height:.2f}" fill="{color}" rx="0.6" />'
        )

    closes = [item["close"] for item in bars]
    for averages, color, label in (
        (_rolling_sma(closes, 5), "#315f9e", "Short SMA"),
        (_rolling_sma(closes, 20), "#9b6b27", "Long SMA"),
    ):
        points = []
        for index, value in enumerate(averages):
            if value is None:
                continue
            xpos = left + step * (index + 0.5)
            points.append(f"{xpos:.2f},{y(value):.2f}")
        if len(points) >= 2:
            svg.append(
                f'<polyline points="{" ".join(points)}" fill="none" stroke="{color}" '
                'stroke-width="2" stroke-linejoin="round" stroke-linecap="round" />'
            )

    label_indices = sorted({0, len(bars) // 2, len(bars) - 1})
    for index in label_indices:
        timestamp = bars[index]["timestamp"]
        label = timestamp[:10] if len(timestamp) >= 10 else timestamp
        xpos = left + step * (index + 0.5)
        svg.append(
            f'<text x="{xpos:.2f}" y="{height-13:.1f}" text-anchor="middle" '
            f'font-size="11" fill="#667085">{escape(label)}</text>'
        )

    svg.extend(
        [
            f'<line x1="{left:.1f}" y1="{height-30:.1f}" x2="{left+18:.1f}" y2="{height-30:.1f}" '
            'stroke="#315f9e" stroke-width="2" />',
            f'<text x="{left+24:.1f}" y="{height-26:.1f}" font-size="11" fill="#667085">Short SMA</text>',
            f'<line x1="{left+112:.1f}" y1="{height-30:.1f}" x2="{left+130:.1f}" y2="{height-30:.1f}" '
            'stroke="#9b6b27" stroke-width="2" />',
            f'<text x="{left+136:.1f}" y="{height-26:.1f}" font-size="11" fill="#667085">Long SMA</text>',
            '</svg>',
        ]
    )

    signal_price = row.get("latest_trade_price")
    if signal_price is None:
        signal_price = row.get("tss_last_price")
    signals = [
        f"Return {signal_direction(row.get('return_1_period'))}",
        f"Momentum {signal_direction(row.get('momentum'))}",
        f"Price vs Short SMA {relative_state(signal_price, row.get('sma_short'))}",
        f"Short SMA vs Long {relative_state(row.get('sma_short'), row.get('sma_long'))}",
    ]
    chips = "".join(
        f'<span class="cats-signal-chip">{escape(value)}</span>' for value in signals
    )
    return (
        '<div class="cats-market-chart">'
        '<div class="cats-market-chart-title">Candlestick Market View + TSS Signals</div>'
        + "".join(svg)
        + f'<div class="cats-signal-strip">{chips}</div>'
        + '</div>'
    )


def report_row(
    label: str,
    value: Any,
    *,
    secondary: str | None = None,
    highlight: bool = False,
) -> str:
    rendered_value = escape(display_status(value))
    if highlight and display_status(value) != "—":
        rendered_value = f'<span class="cats-live-time">{rendered_value}</span>'
    if secondary:
        rendered_value += "&nbsp;&nbsp;&nbsp;" + escape(secondary)
    return (
        '<div class="cats-report-row">'
        f'<div class="cats-report-label">{escape(label)}</div>'
        f'<div class="cats-report-value">{rendered_value}</div>'
        '</div>'
    )


def report_card(
    title: str,
    rows: Iterable[
        tuple[str, Any, str | None] | tuple[str, Any, str | None, bool]
    ],
    *,
    subtitle: str | None = None,
    narrative_label: str | None = None,
    narrative: str | None = None,
    note: str | None = None,
    extra_html: str = "",
    css_class: str = "",
) -> None:
    parts = [
        f'<div class="cats-report-card {escape(css_class)}">',
        f'<div class="cats-report-title">{escape(title)}</div>',
    ]
    if subtitle:
        parts.append(f'<div class="cats-report-subtitle">{escape(subtitle)}</div>')
    parts.append('<div class="cats-report-rule"></div>')
    for row in rows:
        if len(row) == 4:
            label, value, secondary, highlight = row
        else:
            label, value, secondary = row
            highlight = False
        parts.append(report_row(label, value, secondary=secondary, highlight=highlight))
    if narrative_label:
        parts.append(f'<div class="cats-report-subheading">{escape(narrative_label)}</div>')
    if narrative:
        parts.append(f'<div class="cats-report-narrative">{escape(narrative)}</div>')
    if extra_html:
        parts.append(extra_html)
    if note:
        parts.append(f'<div class="cats-report-note">{escape(note)}</div>')
    parts.append("</div>")
    st.markdown("".join(parts), unsafe_allow_html=True)


def subheading(text_value: str) -> str:
    return f'<div class="cats-report-subheading">{escape(text_value)}</div>'


def simple_line(text_value: str) -> str:
    return f'<div class="cats-report-narrative">{escape(text_value)}</div>'


_ISO_TIMESTAMP_RE = re.compile(
    r"\b\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})\b"
)


def _presentation_narrative(raw: str) -> str:
    """Normalize timestamp prose for readability without changing persisted assessment text."""
    text_value = raw
    text_value = re.sub(
        r"relative to (?:the )?assessment time\s+" + _ISO_TIMESTAMP_RE.pattern,
        "relative to this assessment",
        text_value,
        flags=re.IGNORECASE,
    )
    text_value = re.sub(
        r"assessment time\s+" + _ISO_TIMESTAMP_RE.pattern,
        "assessment time shown above",
        text_value,
        flags=re.IGNORECASE,
    )
    return _ISO_TIMESTAMP_RE.sub(
        lambda match: operator_timestamp(match.group(0)).replace("   ", " "),
        text_value,
    )


def assessment_narrative_sections_html(summary: Any) -> str:
    """Presentation-only grouping of a persisted TAA narrative.

    The underlying assessment text is not changed. Sentences are grouped into
    external/news evidence, deterministic market/technical analysis, and a
    residual synthesis section so the operator can scan the reasoning sources.
    """
    raw = _presentation_narrative(str(summary or "").strip())
    if not raw:
        return (
            '<div class="cats-reasoning-panel">'
            + subheading("Reasoning / assessment narrative")
            + simple_line("—")
            + '</div>'
        )

    sentences = [
        part.strip()
        for part in re.split(r"(?<=[.!?])\s+(?=[A-Z0-9])", raw)
        if part.strip()
    ]
    if not sentences:
        sentences = [raw]

    technical_terms = (
        "price", "stock", "return", "momentum", "moving average", "sma",
        "volatility", "liquidity", "volume", "trend", "spread", "technical",
        "market participation", "last trade",
    )
    evidence_terms = (
        "evidence", "news", "source", "reported", "announcement", "leadership",
        "executive chairman", "cook", "ternus", "lawsuit", "patent", "ai space",
        "manufacturing", "china", "geopolitical", "company", "market value",
    )

    evidence: list[str] = []
    technical: list[str] = []
    synthesis: list[str] = []
    for sentence in sentences:
        lowered = sentence.lower()
        if any(term in lowered for term in evidence_terms):
            evidence.append(sentence)
        elif any(term in lowered for term in technical_terms):
            technical.append(sentence)
        else:
            synthesis.append(sentence)

    def section(title: str, items: list[str]) -> str:
        if not items:
            return ""
        bullets = "".join(f"<li>{escape(item)}</li>" for item in items)
        return (
            '<div class="cats-assessment-section">'
            f'<div class="cats-assessment-section-title">{escape(title)}</div>'
            f'<ul class="cats-assessment-bullets">{bullets}</ul>'
            '</div>'
        )

    return (
        '<div class="cats-reasoning-panel">'
        + subheading("Reasoning / assessment narrative")
        + section("News / External Evidence", evidence)
        + section("Market / Technical Analysis", technical)
        + section("Assessment Synthesis", synthesis)
        + '</div>'
    )


def live_value_changed(key: str, value: Any) -> bool:
    """Return True only when a live value changed since its previous render."""
    normalized = display_status(value)
    state_key = f"_cats_live_value::{key}"
    previous = st.session_state.get(state_key)
    st.session_state[state_key] = normalized
    return normalized != "—" and normalized != previous


def flow_instrument_symbol(model: CatsUiReadModel, flow_id: str, row: dict[str, Any] | None = None) -> str:
    """Best-effort read-only projection of the instrument associated with a persisted flow."""
    row = row or {}
    for key in ("symbol", "instrument", "instrument_symbol", "financial_instrument"):
        value = row.get(key)
        if value:
            try:
                return normalize_symbol(str(value))
            except Exception:
                pass

    try:
        taa_projection = model.taa_reasoning(flow_id) or {}
        for key in ("symbol", "instrument", "instrument_symbol", "financial_instrument"):
            value = taa_projection.get(key)
            if value:
                return normalize_symbol(str(value))
    except Exception:
        pass

    try:
        transition_projection = model.selected_decision_transition(flow_id) or []
        if transition_projection:
            value = transition_projection[0].get("symbol") or transition_projection[0].get("instrument")
            if value:
                return normalize_symbol(str(value))
    except Exception:
        pass

    try:
        execution_projection = model.execution_snapshot(flow_id) or {}
        value = execution_projection.get("symbol") or execution_projection.get("instrument")
        if value:
            return normalize_symbol(str(value))
    except Exception:
        pass

    return ""


@st.cache_resource
def read_model() -> CatsUiReadModel:
    settings = get_settings()
    engine = create_engine_from_settings(settings)
    return CatsUiReadModel(engine)


st.title("CATS V2ET — Autonomous Trading System")

try:
    model = read_model()
    db = model.database_identity()
except Exception as exc:
    st.error(f"Database connection failed: {exc}")
    st.stop()

environment_name = os.getenv("CATS_ENVIRONMENT", "UNKNOWN")
qwen_endpoint = (os.getenv("QWEN_ENDPOINT_URL") or "").strip()
qwen_token = (os.getenv("CATS_QWEN_SESSION_TOKEN") or "").strip()
project_root = Path(__file__).resolve().parents[1]


@st.cache_data(ttl=10, show_spinner=False)
def cached_qwen_health(endpoint_url: str, session_token: str) -> dict[str, Any]:
    return probe_qwen_health(endpoint_url, session_token)


qwen_probe = cached_qwen_health(qwen_endpoint, qwen_token)
qwen_ready = bool(qwen_probe.get("ready"))
loop_running = main_loop_is_running(project_root)
loop_status = read_main_loop_status(project_root)
visible_startup_recovery = (
    loop_status.get("startup_recovery")
    or st.session_state.get("cats_last_startup_recovery")
)
qwen_display = (
    "READY"
    if qwen_ready
    else "UNREACHABLE"
    if qwen_endpoint and qwen_token
    else "NOT CONFIGURED"
)

runtime_activation = str(loop_status.get("authority_chain") or MANUAL_TRIGGER_ONLY).upper()
if "cats_operating_mode" not in st.session_state:
    st.session_state["cats_operating_mode"] = (
        PAPER_EXECUTION_MODE if runtime_activation == AUTO_PAPER_EXECUTION else EVALUATION_MODE
    )
if "cats_auto_cadence_minutes" not in st.session_state:
    runtime_seconds = float(loop_status.get("auto_execution_interval_seconds") or 600.0)
    st.session_state["cats_auto_cadence_minutes"] = max(5, min(60, int(round(runtime_seconds / 60.0))))
if "cats_auto_paper_confirm" not in st.session_state:
    st.session_state["cats_auto_paper_confirm"] = runtime_activation == AUTO_PAPER_EXECUTION and loop_running
operating_mode = st.session_state["cats_operating_mode"]
paper_execution_enabled = operating_mode == PAPER_EXECUTION_MODE
sys_profile = active_sys_profile()
sys_profile_label = sys_profile_display(sys_profile)

with st.sidebar:
    report_card(
        "System",
        [
            ("Environment", environment_name, None),
            ("Database", db.get("database") or "—", None),
            ("DB", "CONNECTED", None),
            ("Qwen", qwen_display, None),
            ("Embeddings", "LOCAL / CPU", None),
            ("Main Loop", "RUNNING" if loop_running else "STOPPED", None),
            ("Startup Recovery", startup_recovery_label(visible_startup_recovery), None),
            ("Operating Mode", operating_mode, None),
            (
                "Evaluation Cadence",
                (
                    f"{float(loop_status.get('auto_execution_interval_seconds')) / 60:.0f} min"
                    if runtime_activation == AUTO_PAPER_EXECUTION and loop_status.get("auto_execution_interval_seconds")
                    else "—"
                ),
                None,
            ),
            ("SYS Profile", sys_profile_label, None),
        ],
        note=None if qwen_ready else str(qwen_probe.get("detail") or "Qwen is not ready."),
        css_class="cats-sidebar-system",
    )

    if loop_running:
        if st.button("STOP CATS SYSTEM", type="primary", use_container_width=True, key="sidebar_stop_cats"):
            stop_main_loop(project_root)
            st.success("CATS stop requested. The monitoring loop will shut down cleanly.")
            st.rerun()
    else:
        sidebar_load_disabled = environment_name.upper() != "PAPER"
        if st.button(
            "LOAD CATS SYSTEM",
            type="primary",
            use_container_width=True,
            disabled=sidebar_load_disabled,
            key="sidebar_load_cats",
        ):
            st.session_state["cats_sidebar_load_requested"] = True

    sidebar_symbol = str((loop_status.get("symbols") or [st.session_state.get("cats_financial_instrument", "AAPL")])[0]).upper()
    sidebar_news_url = ""
    for item in (loop_status.get("news") or []):
        item_symbols = {str(value).upper() for value in (item.get("symbols") or [])}
        candidate_url = str(item.get("url") or "").strip()
        if candidate_url and (not item_symbols or sidebar_symbol in item_symbols):
            sidebar_news_url = candidate_url
            break

    if (
        loop_running
        and paper_execution_enabled
        and runtime_activation != AUTO_PAPER_EXECUTION
    ):
        if st.session_state.pop("_cats_reset_quick_confirm", False):
            st.session_state["cats_sidebar_quick_confirm"] = False
        sidebar_quick_confirm = st.checkbox(
            "Authorize next PAPER evaluation",
            key="cats_sidebar_quick_confirm",
            help="Uses the latest monitored Alpaca news item as evidence for one full CATS PAPER evaluation.",
        )
        sidebar_quick_clicked = st.button(
            "RUN CATS EVALUATION NOW",
            type="primary",
            use_container_width=True,
            disabled=(not qwen_ready or not sidebar_news_url or not sidebar_quick_confirm),
            key="sidebar_run_cats_now",
        )
        if not sidebar_news_url:
            st.caption("No monitored news URL is available yet; use Additional Evidence below for a custom source.")
        if sidebar_quick_clicked:
            try:
                command = build_paper_command(
                    project_root=project_root,
                    symbol=sidebar_symbol,
                    evidence_reference=sidebar_news_url,
                    qwen_endpoint_url=qwen_endpoint,
                )
                with st.spinner("Running one full CATS PAPER evaluation..."):
                    completed = subprocess.run(
                        command,
                        cwd=project_root,
                        env=os.environ.copy(),
                        capture_output=True,
                        text=True,
                        timeout=900,
                        check=False,
                    )
                output = (completed.stdout or "") + ("\n" + completed.stderr if completed.stderr else "")
                st.session_state["cats_last_run_output"] = output[-12000:]
                st.session_state["cats_last_run_returncode"] = completed.returncode
                if completed.returncode != 0:
                    st.error(describe_launcher_failure(output, completed.returncode))
                else:
                    st.session_state["_cats_reset_quick_confirm"] = True
                    st.cache_resource.clear()
                    st.success("CATS evaluation completed.")
                    st.rerun()
            except subprocess.TimeoutExpired:
                st.error("CATS PAPER evaluation exceeded the 15-minute UI timeout. Inspect persisted state before retrying.")
            except Exception as exc:
                st.error(f"CATS PAPER evaluation blocked: {exc}")


    component_monitoring = "MONITORING" if loop_running else "STANDBY"
    taa_state = "MONITORING" if loop_running else ("READY" if qwen_ready else "NOT READY")
    report_card(
        "CATS Components",
        [
            ("TSS", "Trading Signal Service", f"{component_monitoring} · measures"),
            ("TAA", "Trading Assessment Agent", f"{taa_state} · interprets"),
            ("PMA", "Portfolio Management Agent", "STANDBY · decides"),
            ("PMS", "Portfolio Management Service", "STANDBY · optimizes"),
            ("SYS", "System Validation Authority", "STANDBY · validates"),
            ("TEA", "Trading Execution Agent", "STANDBY · execution strategy"),
            ("TES", "Trading Execution System", "STANDBY · broker mechanisms"),
            ("DAS", "Derivatives Analysis Service", "NOT IN V2ET"),
        ],
        note="Operational order: market data → TSS → TAA → PMA → PMS when required → SYS → TEA → TES ↔ Alpaca.",
        css_class="cats-components",
    )

status_symbols = list(loop_status.get("symbols") or [])
if "cats_financial_instrument" not in st.session_state:
    st.session_state["cats_financial_instrument"] = status_symbols[0] if len(status_symbols) == 1 else "AAPL"

st.subheader("CATS System")
st.markdown("**Operating Mode**")
operating_mode = st.radio(
    "CATS Operating Mode",
    OPERATING_MODES,
    key="cats_operating_mode",
    horizontal=True,
    disabled=loop_running,
    label_visibility="collapsed",
    help=(
        "EVALUATION / MONITORING runs observation and TAA interpretation without broker execution. "
        "PAPER EXECUTION runs full CATS evaluations on cadence; SYS validation gates any order before TEA/TES."
    ),
)
paper_execution_enabled = operating_mode == PAPER_EXECUTION_MODE
if sys_profile == SYS_PROFILE_AGGRESSIVE_PAPER_TEST:
    st.warning(
        "AGGRESSIVE — PAPER TEST. SYS/PMS limits are relaxed for PAPER testing; "
        "SYS validation and broker reconciliation remain active."
    )
if paper_execution_enabled:
    st.warning(
        "PAPER EXECUTION. CATS may initiate full evaluations on the configured cadence. "
        "PMA proposes Portfolio intent; SYS must PASS before execution can proceed."
    )
else:
    st.info(
        "EVALUATION / MONITORING. TSS and TAA operate continuously; no broker orders are submitted."
    )

st.markdown("**Financial Instrument**")
predefined_symbols = list(TECH_EQUITIES)
current_symbol = st.session_state.get("cats_financial_instrument", "AAPL")
if current_symbol not in predefined_symbols:
    predefined_symbols = [current_symbol] + predefined_symbols
symbol_input = st.selectbox(
    "Selected Financial Instrument",
    predefined_symbols,
    key="cats_financial_instrument",
    format_func=lambda value: instrument_label(value),
    disabled=loop_running,
    label_visibility="collapsed",
    help="V2ET operates on one selected equity per monitoring/evaluation cycle. Stop the main loop before changing it.",
)
try:
    selected_symbol = normalize_symbol(symbol_input)
    symbol_error = None
except Exception as exc:
    selected_symbol = ""
    symbol_error = str(exc)
    st.error(f"Financial Instrument is not valid: {exc}")

previous_selected_symbol = st.session_state.get("_cats_previous_selected_symbol")
if selected_symbol and previous_selected_symbol != selected_symbol:
    st.session_state["_cats_previous_selected_symbol"] = selected_symbol
    st.session_state.pop("flow_selector", None)

st.caption(
    "One selected equity is processed per V2ET cycle. Stop the main loop before changing instruments."
)

# There are exactly two operator modes. The internal activation value is an
# implementation detail: EVALUATION / MONITORING never reaches broker execution,
# while PAPER EXECUTION periodically invokes the existing full authority chain.
effective_activation_mode = (
    AUTO_PAPER_EXECUTION if paper_execution_enabled else MANUAL_TRIGGER_ONLY
)
auto_cadence_minutes = int(st.session_state.get("cats_auto_cadence_minutes", 10))
auto_confirm = bool(st.session_state.get("cats_auto_paper_confirm", False))

if paper_execution_enabled:
    st.markdown("**Full Evaluation Cadence**")
    auto_cadence_minutes = int(
        st.number_input(
            "Full Evaluation Cadence (minutes)",
            min_value=5,
            max_value=60,
            step=5,
            key="cats_auto_cadence_minutes",
            disabled=loop_running,
            label_visibility="collapsed",
            help=(
                "CATS may initiate a full PAPER evaluation at this cadence when a fresh FINAL TAA assessment "
                "and usable evidence are available. PMA proposes intent and SYS independently validates it."
            ),
        )
    )
    auto_confirm = st.checkbox(
        "I authorize CATS to execute through Alpaca PAPER when SYS approves an order while this system session is running.",
        key="cats_auto_paper_confirm",
        disabled=loop_running,
        help="This enables PAPER execution for the running session; it does not bypass PMA, SYS, TEA, or TES.",
    )
    st.caption(
        "Full evaluations may run on the configured cadence. SYS PASS is required before an order can proceed to TEA/TES and Alpaca PAPER."
    )
else:
    # Do not carry a prior PAPER authorization into a later evaluation-only session.
    if not loop_running:
        st.session_state["cats_auto_paper_confirm"] = False
    auto_confirm = False

if st.session_state.pop("cats_sidebar_load_requested", False):
    if environment_name.upper() != "PAPER":
        st.error("CATS system load is blocked because CATS_ENVIRONMENT is not PAPER.")
    else:
        try:
            # Recovery is first. It needs PostgreSQL + Alpaca PAPER, not Qwen.
            with st.spinner("Reconciling persisted PAPER execution state against Alpaca..."):
                startup_recovery, recovery_output, recovery_returncode = run_startup_recovery(project_root)
            st.session_state["cats_last_startup_recovery"] = startup_recovery
            st.session_state["cats_last_startup_recovery_output"] = recovery_output

            recovery_status = str(startup_recovery.get("status") or "").upper()
            if recovery_status == "BLOCKED" or recovery_returncode != 0:
                st.error(
                    str(startup_recovery.get("detail") or "Startup recovery blocked normal CATS operation.")
                )
            elif not qwen_ready:
                st.success(
                    str(startup_recovery.get("detail") or "Startup recovery completed.")
                )
                st.warning(
                    "Qwen is not ready, so CATS will not start the normal TAA/PMA operating loop. "
                    "Deterministic startup recovery has already completed and does not require Qwen."
                )
            elif symbol_error:
                st.error(f"Financial Instrument is not valid: {symbol_error}")
            elif paper_execution_enabled and not auto_confirm:
                st.error("Authorize Alpaca PAPER execution before starting new PAPER evaluations.")
            else:
                with st.spinner("Running CATS preflight and starting the main operating loop..."):
                    preflight = subprocess.run(
                        [sys.executable, str(project_root / "scripts" / "external_run_preflight.py")],
                        cwd=project_root,
                        env=os.environ.copy(),
                        capture_output=True,
                        text=True,
                        timeout=300,
                        check=False,
                    )
                preflight_output = (preflight.stdout or "") + (
                    "\n" + preflight.stderr if preflight.stderr else ""
                )
                st.session_state["cats_last_preflight_output"] = preflight_output[-12000:]
                if preflight.returncode != 0:
                    st.error(
                        f"CATS system load failed during preflight (exit code {preflight.returncode}). "
                        "Open the preflight output below for the specific failed dependency."
                    )
                else:
                    loop_env = os.environ.copy()
                    loop_env["CATS_MONITOR_SYMBOLS"] = selected_symbol
                    loop_env["CATS_EXECUTION_ACTIVATION"] = effective_activation_mode
                    if effective_activation_mode == AUTO_PAPER_EXECUTION:
                        loop_env["CATS_AUTO_PAPER_CONFIRM"] = "YES"
                        loop_env["CATS_AUTO_PAPER_SECONDS"] = str(auto_cadence_minutes * 60)
                    else:
                        loop_env.pop("CATS_AUTO_PAPER_CONFIRM", None)
                    pid = start_main_loop(project_root, env=loop_env)
                    st.success(
                        f"CATS main operating loop started for {selected_symbol} (PID {pid}) in {operating_mode}."
                    )
                    st.rerun()
        except subprocess.TimeoutExpired:
            st.error("CATS startup recovery or preflight exceeded the 5-minute UI timeout.")
        except Exception as exc:
            st.error(f"CATS system could not be loaded: {type(exc).__name__}: {exc}")

if st.session_state.get("cats_last_startup_recovery_output"):
    with st.expander("Last startup recovery output", expanded=False):
        st.code(st.session_state["cats_last_startup_recovery_output"], language="text")

if st.session_state.get("cats_last_preflight_output"):
    with st.expander("Last CATS system preflight output", expanded=False):
        st.code(st.session_state["cats_last_preflight_output"], language="text")


@st.fragment(run_every=5)
def render_operating_loop_activity() -> None:
    status = read_main_loop_status(project_root)
    running = main_loop_is_running(project_root)
    if not status and not running:
        report_card(
            "Main Operating Loop",
            [("Status", "NOT LOADED", None)],
            note="Press LOAD CATS SYSTEM to start continuous market and Alpaca-news monitoring.",
        )
        return

    startup_recovery = status.get("startup_recovery") or {}
    if str(startup_recovery.get("status") or "").upper() == "BLOCKED":
        st.error(str(startup_recovery.get("detail") or "Startup recovery blocked normal CATS operation."))

    report_card(
        "Main Operating Loop",
        [
            ("Status", status.get("status") or ("RUNNING" if running else "STOPPED"), None),
            ("Startup Recovery", startup_recovery_label(status.get("startup_recovery")), None),
            ("System Operating Mode", operating_mode, None),
            ("SYS Behavior Profile", sys_profile_label, None),
            ("Loop Mode", status.get("mode") or "MONITORING", None),
            ("Cycles", status.get("cycle_count", 0), None),
            ("Financial Instrument", instrument_label((status.get("symbols") or [selected_symbol or "—"])[0]), None),
            ("Last Market Cycle", operator_timestamp(status.get("last_market_cycle_at")), None, live_value_changed("loop:last_market_cycle", status.get("last_market_cycle_at")) if running else False),
            ("Last News Check", operator_timestamp(status.get("last_news_check_at")), None, live_value_changed("loop:last_news_check", status.get("last_news_check_at")) if running else False),
            ("Last TAA Assessment", operator_timestamp(status.get("last_taa_assessment_at")), None, live_value_changed("loop:last_taa_assessment", status.get("last_taa_assessment_at")) if running else False),
            ("Interpretation", status.get("interpretation") or "DISABLED", None),
            ("Authority Chain", "TAA → PMA → SYS → TEA → TES", None),
            ("Market Signal Flow", "Alpaca → TSS → TAA", None),
            ("Optimization", "PMA ↔ PMS (when required)", None),
            ("Broker Interface", "TEA → TES ↔ Alpaca", None),
            (
                "Full Evaluation Cadence",
                (
                    f"{float(status.get('auto_execution_interval_seconds')) / 60:.0f} min"
                    if paper_execution_enabled and status.get("authority_chain") == AUTO_PAPER_EXECUTION and status.get("auto_execution_interval_seconds")
                    else "—"
                ),
                None,
            ),
            (
                "Last Full Evaluation",
                operator_timestamp(status.get("last_auto_execution_at")) if paper_execution_enabled else "—",
                status.get("last_auto_execution_state") if paper_execution_enabled and status.get("authority_chain") == AUTO_PAPER_EXECUTION else None,
                live_value_changed("loop:last_auto_execution", status.get("last_auto_execution_at")) if running and paper_execution_enabled else False,
            ),
        ],
        note=(
            "PAPER EXECUTION is active. Full evaluations may run on cadence; PMA proposes intent and SYS must PASS before execution can proceed."
            if paper_execution_enabled and status.get("authority_chain") == AUTO_PAPER_EXECUTION
            else "EVALUATION / MONITORING is active. TSS/TAA continue operating; broker execution is disabled."
        ),
    )

    market_rows = status.get("market") or []
    for row in market_rows[:8]:
        latest = row.get("latest_trade_price")
        latest_secondary = None if latest is None else f"latest trade ${float(latest):,.2f}"
        report_card(
            f"TSS | Market Surveillance — {instrument_label(row.get('symbol'))}",
            [
                ("Observation Time", operator_timestamp(status.get("last_market_cycle_at")), None, live_value_changed(f"tss:observation:{row.get('symbol')}", status.get("last_market_cycle_at")) if running else False),
                ("Latest Trade", "—" if latest is None else f"${float(latest):,.2f}", None),
                ("TSS Daily Price", "—" if row.get("tss_last_price") is None else f"${float(row['tss_last_price']):,.2f}", None),
                ("Momentum", "—" if row.get("momentum") is None else f"{float(row['momentum']) * 100:.2f}%", None),
                ("Volatility", "—" if row.get("annualized_volatility") is None else f"{float(row['annualized_volatility']) * 100:.2f}%", None),
                ("Average Volume", "—" if row.get("average_volume") is None else f"{float(row['average_volume']):,.0f}", None),
            ],
            subtitle="Raw Quantitative Market Measurements",
            extra_html=candlestick_signal_chart_html(row),
            note=None if latest_secondary else "Latest-trade endpoint unavailable; TSS daily measurements remain visible.",
        )

        signal_price = row.get("latest_trade_price") if row.get("latest_trade_price") is not None else row.get("tss_last_price")
        report_card(
            f"TSS | Signal Assessment — {instrument_label(row.get('symbol'))}",
            [
                ("Signal Assessment Time", operator_timestamp(status.get("last_market_cycle_at")), None, live_value_changed(f"tss:signal:{row.get('symbol')}", status.get("last_market_cycle_at")) if running else False),
                ("Signal Scan", "ACTIVE" if running else "LAST OBSERVATION", None),
                ("1-Period Return", signal_direction(row.get("return_1_period")), "—" if row.get("return_1_period") is None else f"{float(row['return_1_period']) * 100:.2f}%"),
                ("Momentum", signal_direction(row.get("momentum")), "—" if row.get("momentum") is None else f"{float(row['momentum']) * 100:.2f}%"),
                ("Price vs Short SMA", relative_state(signal_price, row.get("sma_short")), None),
                ("Short SMA vs Long", relative_state(row.get("sma_short"), row.get("sma_long")), None),
                ("Annualized Volatility", "—" if row.get("annualized_volatility") is None else f"{float(row['annualized_volatility']) * 100:.2f}%", None),
                ("Liquidity Proxy", usd(row.get("liquidity_proxy")), None),
            ],
            subtitle="Deterministic Trading Signals Derived from Market Measurements",
            note=(
                "Deterministic trading signals derived from TSS market measurements. Not a BUY/SELL "
                "recommendation; TAA interprets these signals in financial context."
            ),
        )

    news_rows = status.get("news") or []
    if news_rows:
        latest_news = news_rows[0]
        news_symbols = latest_news.get("symbols") or []
        if isinstance(news_symbols, (list, tuple)):
            news_symbol = news_symbols[0] if news_symbols else (selected_symbol or "—")
        else:
            news_symbol = str(news_symbols).split(",", 1)[0].strip() or (selected_symbol or "—")
        report_card(
            f"TAA | Latest Alpaca News — {instrument_label(news_symbol)}",
            [
                ("Monitoring", "ACTIVE" if running else "STOPPED", None),
                ("Last Check Result", status.get("news_status") or "—", None),
                ("Last News Check", operator_timestamp(status.get("last_news_check_at")), None, live_value_changed(f"news:last_check:{news_symbol}", status.get("last_news_check_at")) if running else False),
                ("Source", latest_news.get("source") or "—", None),
                ("Symbols", ", ".join(latest_news.get("symbols") or []) or "—", None),
                ("Published", operator_timestamp(latest_news.get("created_at")), None),
            ],
            narrative_label="Headline",
            narrative=latest_news.get("headline") or "—",
            note=latest_news.get("summary") or None,
            css_class="cats-news-card",
        )



    if status.get("last_taa_error"):
        st.error("TAA monitoring degraded: " + str(status.get("last_taa_error")))

    if status.get("last_error"):
        st.error("Main loop degraded: " + str(status.get("last_error")))


render_operating_loop_activity()

if loop_running:
    with st.expander("Main loop technical log", expanded=False):
        st.code(tail_runtime_log(project_root) or "No runtime log output yet.", language="text")

def assessment_outlook(summary) -> str | None:
    """Extract the explicit TAA Outlook statement from Assessment.summary."""
    for line in str(summary or "").splitlines():
        line = line.strip()
        if not line.lower().startswith("outlook:"):
            continue
        value = line.split(":", 1)[1].strip().upper()
        if value in {"FAVORABLE", "NEUTRAL", "ADVERSE"}:
            return value
    return None


@st.fragment(run_every=5)
def render_taa_monitoring() -> None:
    status = read_main_loop_status(project_root)
    assessment_rows = status.get("assessments") or []
    for assessment in assessment_rows[:8]:
        confidence = assessment.get("confidence")
        metrics = assessment.get("reasoning_metrics") or {}
        inference = metrics.get("inference_seconds")
        evidence_used = assessment.get("evidence_items_used")
        report_card(
            f"TAA | Live Monitoring Assessment — {instrument_label(assessment.get('symbol') or selected_symbol)}",
            [
                ("Horizon", assessment.get("horizon") or "—", None),
                ("Outlook", assessment_outlook(assessment.get("summary")) or "—", None),
                ("Confidence", "—" if confidence is None else f"{float(confidence) * 100:.2f}%", None),
                ("Assessment Date Time", operator_timestamp(assessment.get("assessed_at") or status.get("last_taa_assessment_at")), None, live_value_changed(f"taa:assessment_time:{assessment.get('symbol') or selected_symbol}", assessment.get("assessed_at") or status.get("last_taa_assessment_at")) if main_loop_is_running(project_root) else False),
                ("Valid Until", operator_timestamp(assessment.get("valid_until")), None),
                ("Evidence Used", "—" if evidence_used is None else evidence_used, None),
                ("Qwen Inference", "—" if inference is None else f"{float(inference):.2f} s", None),
            ],
            extra_html=assessment_narrative_sections_html(assessment.get("summary")),
            note=(
                "Live TAA monitoring assessment. In EVALUATION / MONITORING it remains observational; "
                "in PAPER EXECUTION it may trigger a separate full authority-chain evaluation on cadence."
            ),
        )


render_taa_monitoring()

all_flows = model.latest_flows(limit=30)
flows: list[dict[str, Any]] = []
flow_id_key = "flow_id" if all_flows and "flow_id" in all_flows[0] else (next(iter(all_flows[0])) if all_flows else "flow_id")
for flow_row in all_flows:
    candidate_flow_id = str(flow_row.get(flow_id_key))
    if selected_symbol and flow_instrument_symbol(model, candidate_flow_id, flow_row) == selected_symbol:
        flows.append(flow_row)

flow_options = [str(row.get(flow_id_key)) for row in flows]
selected_flow: str | None = None
selected_flow_row: dict[str, Any] = {}

with st.sidebar:
    st.header("Flow Explorer")
    if flow_options:
        newest_flow = flow_options[0]
        previously_seen_latest = st.session_state.get("_cats_latest_flow_seen")
        current_selection = st.session_state.get("flow_selector")
        if current_selection not in flow_options or previously_seen_latest is None or previously_seen_latest != newest_flow:
            st.session_state["flow_selector"] = newest_flow
        st.session_state["_cats_latest_flow_seen"] = newest_flow
        selected_flow = st.selectbox("Flow", flow_options, key="flow_selector")
    else:
        st.caption(f"No persisted flow available for {selected_symbol or 'the selected instrument'}.")
    if st.button("Refresh database view", use_container_width=True):
        st.cache_resource.clear()
        st.rerun()

selected_is_latest = bool(selected_flow and flow_options and selected_flow == flow_options[0])

if selected_flow:
    selected_flow_row = next(row for row in flows if str(row.get(flow_id_key)) == selected_flow)
    selected_flow_title = (
        "Selected Flow — CURRENT / LATEST"
        if selected_is_latest
        else "Selected Flow — HISTORICAL"
    )
    report_card(
        selected_flow_title,
        [
            ("Flow ID", selected_flow, None),
            ("Status", display_status(selected_flow_row.get("status")), None),
            ("Started", operator_timestamp(selected_flow_row.get("started_at") or selected_flow_row.get("created_at")), None),
            ("Completed", operator_timestamp(selected_flow_row.get("completed_at")), None),
        ],
    )
else:
    report_card(
        "Selected Flow — HISTORICAL",
        [("Status", f"No persisted full CATS flow is available for {selected_symbol or 'the selected instrument'}.", None)],
        note="Historical decision/execution cards remain empty until this instrument has a persisted full evaluation flow.",
    )

# Load the principal human-readable projections once.
taa = model.taa_reasoning(selected_flow) if selected_flow else {}
taa_record = model.first_row_for_flow("TAA_Assessment", selected_flow) if selected_flow else {}
taa_record = taa_record or {}
transition = model.selected_decision_transition(selected_flow) if selected_flow else []
execution = model.execution_snapshot(selected_flow) if selected_flow else {}

# Flow chronology is reconstructed from persisted timestamps only. No timestamp is invented.
pma_record = model.first_row_for_flow("PMA_Portfolio_Decision", selected_flow) if selected_flow else {}
sys_record = model.first_row_for_flow("SYS_Validation_Result", selected_flow) if selected_flow else {}
tea_record = model.first_row_for_flow("TEA_Execution", selected_flow) if selected_flow else {}
execution_result_record = model.first_row_for_flow("TEA_Execution_Result", selected_flow) if selected_flow else {}
pma_record = pma_record or {}
sys_record = sys_record or {}
tea_record = tea_record or {}
execution_result_record = execution_result_record or {}
execution_id = tea_record.get("execution_id")

tea_action_record = _related_row(
    model,
    "TEA_Execution_Action",
    "execution_id",
    execution_id,
    order_candidates=("requested_at", "created_at"),
)
order_record = _related_row(
    model,
    "TES_Order",
    "execution_id",
    execution_id,
    order_candidates=("submitted_at", "created_at"),
)
first_fill_record = _related_row(
    model,
    "TES_Fill",
    "execution_id",
    execution_id,
    order_candidates=("filled_at", "created_at"),
)
final_fill_record = _related_row(
    model,
    "TES_Fill",
    "execution_id",
    execution_id,
    order_candidates=("filled_at", "created_at"),
    descending=True,
)
reconciliation_record = _related_row(
    model,
    "TEA_Reconciliation",
    "execution_id",
    execution_id,
    order_candidates=("reconciled_at", "created_at"),
    descending=True,
)
portfolio_state_record = _related_row(
    model,
    "PMA_Portfolio_State",
    "source_portfolio_decision_id",
    pma_record.get("portfolio_decision_id"),
    order_candidates=("effective_at", "created_at"),
    descending=True,
)

taa_timestamp = _timestamp_value(taa or {}, "created_at", "assessed_at", "assessment_at")
pma_timestamp = _timestamp_value(pma_record, "created_at", "decided_at", "decision_at")
sys_timestamp = _timestamp_value(sys_record, "validated_at", "verified_at", "created_at")
tea_action_timestamp = _timestamp_value(tea_action_record, "requested_at", "created_at")
# In the current persistence contract TEA_Execution_Action.requested_at is populated from the
# broker order submitted_at when available, so it is the safe fallback for historical TES timing.
order_submitted_timestamp = _timestamp_value(order_record, "submitted_at", "created_at") or tea_action_timestamp
first_fill_timestamp = _timestamp_value(first_fill_record, "filled_at", "created_at")
final_fill_timestamp = _timestamp_value(final_fill_record, "filled_at", "created_at")
reconciliation_timestamp = _timestamp_value(reconciliation_record, "reconciled_at", "created_at")
tea_completion_timestamp = _timestamp_value(execution_result_record, "created_at", "completed_at", "executed_at")
portfolio_state_timestamp = _timestamp_value(portfolio_state_record, "effective_at", "created_at")
flow_started_timestamp = _timestamp_value(selected_flow_row, "started_at", "created_at")
flow_completed_timestamp = _timestamp_value(selected_flow_row, "completed_at", "updated_at")

if selected_flow:
    timeline_events = [
        ("Flow Started", flow_started_timestamp),
        ("TAA Assessment", taa_timestamp),
        ("PMA Decision", pma_timestamp),
        ("SYS Verification", sys_timestamp),
        ("TEA Execution Action", tea_action_timestamp),
        ("TES Order Submitted", order_submitted_timestamp),
        ("TES First Fill", first_fill_timestamp),
    ]
    if final_fill_timestamp and final_fill_timestamp != first_fill_timestamp:
        timeline_events.append(("TES Final Fill", final_fill_timestamp))
    timeline_events.extend(
        [
            ("Broker Reconciliation", reconciliation_timestamp),
            ("TEA Execution Completed", tea_completion_timestamp),
            ("Portfolio State Accepted", portfolio_state_timestamp),
            ("Flow Completed", flow_completed_timestamp),
        ]
    )
    chronology_note = (
        "Events follow the CATS causal sequence; persisted timestamps are shown exactly. "
        "Events sharing the same displayed second retain causal order. NOT RECORDED means the "
        "historical schema contains no dedicated timestamp for that event."
    )
    if _timeline_has_recorded_regression(timeline_events):
        chronology_note += " WARNING: a persisted timestamp moves backward across displayed seconds."
    report_card(
        "Selected Flow | Event Timeline",
        _timeline_rows(timeline_events),
        note=chronology_note,
    )

# --- TAA reasoning is the principal AI-facing capstone view. ---
if taa:
    taa_flow_title = "TAA | Current Flow Assessment" if selected_is_latest else "TAA | Historical Flow Assessment"
    persisted_outlook = assessment_outlook(taa.get("summary"))
    report_card(
        taa_flow_title,
        [
            ("Horizon", display_status(taa.get("horizon")), None),
            ("Outlook", "NOT RECORDED" if persisted_outlook in {None, ""} else persisted_outlook, None),
            ("Confidence", pct(taa.get("confidence")), None),
            ("Assessment Date Time", recorded_operator_timestamp(taa_timestamp), None),
        ],
        extra_html=assessment_narrative_sections_html(taa.get("summary")),
        note=(
            "Current/latest full-cycle TAA assessment supplied to PMA; distinct from live monitoring above."
            if selected_is_latest
            else "Historical full-cycle TAA assessment supplied to PMA; distinct from live monitoring above."
        ),
    )
else:
    report_card(
        "TAA | Historical Flow Assessment",
        [("Status", "No persisted TAA assessment is available for this flow.", None)],
    )

# --- Persisted authority-chain projections, one responsibility per card. ---
if transition:
    first_item = transition[0]
    symbol = first_item.get("symbol") or "Instrument"
    current_secondary = approx_usd(first_item.get("current_value_usd")) or "US$ equivalent unavailable"
    target_secondary = approx_usd(first_item.get("target_value_usd")) or "US$ equivalent unavailable"
    delta_secondary = approx_usd(first_item.get("delta_value_usd")) or "US$ equivalent unavailable"

    report_card(
        "PMA | Decision",
        [
            ("Instrument", instrument_label(symbol), None),
            ("Decision", display_status(execution.get("decision_type")), None),
            ("Decision Time", recorded_operator_timestamp(pma_timestamp), None),
            ("Current Position", f"{number(first_item.get('current_quantity'))} shares", current_secondary),
            ("Target Position", f"{number(first_item.get('target_quantity'))} shares", target_secondary),
            ("Required Change", f"{number(first_item.get('delta_quantity'))} shares", delta_secondary),
            ("Target Weight", pct(first_item.get("target_weight")), None),
        ],
        note="PMA owns Portfolio intent for this historical flow.",
    )

    report_card(
        "SYS | Verification",
        [
            ("Result", display_status(execution.get("validation")), None),
            ("Verification Time", recorded_operator_timestamp(sys_timestamp), None),
            ("Decision", display_status(execution.get("decision_type")), None),
            ("Instrument", instrument_label(symbol), None),
        ],
        note="SYS validates the PMA decision against deterministic CATS boundaries.",
    )

    for item in transition:
        symbol = item.get("symbol") or "Instrument"
        current_secondary = approx_usd(item.get("current_value_usd")) or "US$ equivalent unavailable"
        target_secondary = approx_usd(item.get("target_value_usd")) or "US$ equivalent unavailable"
        delta_secondary = approx_usd(item.get("delta_value_usd")) or "US$ equivalent unavailable"

        side = execution.get("order_side") or execution.get("execution_side")
        qty = execution.get("order_quantity") or execution.get("execution_quantity")
        action = (
            f"{side} {number(qty)} shares"
            if side and qty is not None
            else "No broker order recorded"
            if execution.get("execution_status")
            else "—"
        )

        price_type = item.get("reference_price_type")
        if price_type == "BROKER_FILL":
            price_note = (
                "No persisted TSS price was linked to this historical flow. US$ equivalents therefore use "
                "the broker-confirmed fill price from the same execution lineage. These values are display-only "
                "historical equivalents; no live market-data call is made."
            )
            price_source = "BROKER FILL"
        elif item.get("reference_price") is not None:
            price_note = (
                "US$ equivalents are display-only valuations calculated from the persisted "
                f"TSS {price_type} measurement for this flow; no live market-data call is made."
            )
            price_source = str(price_type or "TSS")
        else:
            price_note = (
                "No persisted TSS or broker fill price was available for this historical flow, "
                "so US$ equivalents remain blank."
            )
            price_source = None

        report_card(
            "TEA | Execution Action",
            [
                ("Instrument", instrument_label(symbol), None),
                ("Status", display_status(execution.get("execution_status")), None),
                ("Action", action, None),
                ("Certainty", display_status(execution.get("certainty")), None),
                ("Action Time", recorded_operator_timestamp(tea_action_timestamp), None),
                ("Completed Time", recorded_operator_timestamp(tea_completion_timestamp), None),
                ("Current Position", f"{number(item.get('current_quantity'))} shares", current_secondary),
                ("Target Position", f"{number(item.get('target_quantity'))} shares", target_secondary),
                ("Required Change", f"{number(item.get('delta_quantity'))} shares", delta_secondary),
                ("Target Weight", pct(item.get("target_weight")), None),
                ("Reference Price", usd(item.get("reference_price")), price_source),
            ],
            note=(
                "TEA executes the SYS-approved target without changing Portfolio intent. " + price_note
            ),
        )

        if execution.get("fill_quantity") is not None:
            fill_text = f"{number(execution.get('fill_quantity'))} shares"
            if execution.get("fill_price") is not None:
                fill_text += f" @ {usd(execution.get('fill_price'))}"
        else:
            fill_text = "—"

        final_position = "—"
        final_secondary = None
        if execution.get("final_position_quantity") is not None:
            final_position = f"{number(execution.get('final_position_quantity'))} shares"
            final_secondary = approx_usd(execution.get("final_position_value_usd")) or "US$ equivalent unavailable"

        report_card(
            "TES | Alpaca Order",
            [
                ("Order",
                 f"{execution.get('order_side') or '—'} {number(execution.get('order_quantity'))} shares"
                 if execution.get("order_quantity") is not None else "No order recorded",
                 None),
                ("Submitted", recorded_operator_timestamp(order_submitted_timestamp), None),
                ("Fill", fill_text, None),
                ("Filled", recorded_operator_timestamp(final_fill_timestamp or first_fill_timestamp), None),
                ("Trade Value", usd(execution.get("trade_value_usd")), None),
                ("Reconciliation", display_status(execution.get("reconciliation")), None),
                ("Reconciled", recorded_operator_timestamp(reconciliation_timestamp), None),
                ("Certainty", display_status(execution.get("reconciliation_certainty")), None),
                ("Final Position", final_position, final_secondary),
            ],
            note="TES reports Alpaca order, fill, and reconciliation facts.",
        )
else:
    report_card(
        "PMA | Decision",
        [
            ("Status", "No persisted PMA current-to-target transition is available for this flow.", None),
            ("Decision Time", recorded_operator_timestamp(pma_timestamp), None),
        ],
    )
    report_card(
        "SYS | Verification",
        [
            ("Status", display_status(execution.get("validation")) if execution else "—", None),
            ("Verification Time", recorded_operator_timestamp(sys_timestamp), None),
        ],
    )
    report_card(
        "TEA | Execution Action",
        [
            ("Status", "No persisted execution transition is available for this flow.", None),
            ("Action Time", recorded_operator_timestamp(tea_action_timestamp), None),
            ("Completed Time", recorded_operator_timestamp(tea_completion_timestamp), None),
        ],
    )
    report_card(
        "TES | Alpaca Order",
        [
            ("Status", "No persisted broker order is available for this flow.", None),
            ("Submitted", recorded_operator_timestamp(order_submitted_timestamp), None),
            ("Filled", recorded_operator_timestamp(final_fill_timestamp or first_fill_timestamp), None),
            ("Reconciled", recorded_operator_timestamp(reconciliation_timestamp), None),
        ],
    )

# --- Authority/material chain, also one stage per line. ---
summaries = model.stage_summaries(selected_flow) if selected_flow else []
chain_rows: list[tuple[str, Any, str | None]] = []
for stage in summaries:
    if not stage.available:
        value = "N/A"
        secondary = f"{stage.table_name} not present in this bounded schema"
    elif not stage.flow_linked:
        value = "LINKED"
        secondary = f"{stage.table_name} has no direct flow_id column"
    elif stage.count == 0:
        if str(stage.label).upper() == "TSS":
            value = "CONTEXT ONLY"
            secondary = "TSS values may exist in the TAA assessment context; direct TSS row lineage was not persisted"
        else:
            value = "—"
            secondary = f"No directly linked {stage.table_name} row"
    else:
        value = stage.status or f"{stage.count} row(s)"
        secondary = stage.table_name
    chain_rows.append((stage.label, value, secondary))

if chain_rows:
    report_card(
        "CATS | Authority / Material Flow",
        chain_rows,
        css_class="cats-report-chain",
    )
else:
    report_card(
        "CATS | Authority / Material Flow",
        [("Status", f"No persisted authority-chain flow is available for {selected_symbol or 'the selected instrument'}.", None)],
        css_class="cats-report-chain",
    )

st.subheader("CATS | Additional Evidence / Full Evaluation")

auto_runtime_active = (
    loop_running and str(read_main_loop_status(project_root).get("authority_chain") or "").upper() == AUTO_PAPER_EXECUTION
)
if auto_runtime_active:
    st.info(
        "PAPER EXECUTION is active. The running loop may trigger full evaluations from monitored evidence; "
        "manual RUN CATS EVALUATION is disabled while an unattended PAPER session is running to prevent overlapping flows."
    )

run_clicked = False
confirm_paper = False
evidence_mode = st.session_state.get("cats_evidence_mode", "Website URL")
evidence_url_input = ""
uploaded_evidence = None

if not paper_execution_enabled:
    st.caption(
        f"Selected instrument: {selected_symbol or '—'}. PAPER execution is unavailable while "
        "CATS is in EVALUATION / MONITORING mode."
    )
    st.info(
        "Broker-order controls are locked by the selected operating mode. Switch CATS to PAPER EXECUTION "
        "to expose the full authority-chain evaluation control."
    )
else:
    st.caption(
        f"Optional human-supplied evidence for the selected instrument ({selected_symbol or '—'}). "
        "Running a CATS evaluation activates one complete authority-chain cycle under PAPER EXECUTION mode. "
        "CATS determines whether a Portfolio change is required and whether any Alpaca PAPER order should be submitted."
    )

    evidence_mode = st.radio(
        "Evidence Source",
        ["Website URL", "Local File"],
        key="cats_evidence_mode",
        horizontal=True,
    )

    with st.form("cats_paper_run_form", clear_on_submit=False):
        if evidence_mode == "Website URL":
            evidence_url_input = st.text_input(
                "Website URL",
                placeholder="https://example.com/public-financial-evidence",
            )
        else:
            uploaded_evidence = st.file_uploader(
                "Local File",
                type=["txt", "md", "html", "htm", "docx"],
                help="Supported local evidence types: TXT, MD, HTML, HTM, DOCX.",
            )

        st.caption(
            f"Operating Mode: {operating_mode}  |  Environment: {environment_name}  |  "
            f"Qwen: {'READY' if qwen_ready else 'NOT READY'}  |  Embeddings: LOCAL / CPU"
        )
        confirm_paper = st.checkbox(
            "I authorize CATS to execute through Alpaca PAPER if PMA proposes an order and SYS approves it."
        )
        run_clicked = st.form_submit_button(
            "RUN CATS EVALUATION",
            type="primary",
            disabled=(
                environment_name.upper() != "PAPER"
                or not qwen_ready
                or bool(symbol_error)
                or auto_runtime_active
            ),
        )

    if environment_name.upper() != "PAPER":
        st.error("Execution entry is blocked because CATS_ENVIRONMENT is not PAPER.")
    elif not qwen_ready:
        st.info(
            "Execution entry is disabled until both QWEN_ENDPOINT_URL and "
            "CATS_QWEN_SESSION_TOKEN are loaded in the Streamlit process."
        )

if run_clicked:
    if not paper_execution_enabled:
        st.error("PAPER execution is blocked while CATS is in EVALUATION / MONITORING mode.")
    elif not confirm_paper:
        st.error("PAPER confirmation is required before CATS can start.")
    else:
        try:
            symbol = selected_symbol
            if not symbol:
                raise ValueError("Choose a valid Financial Instrument before starting CATS.")
            staged = None
            if evidence_mode == "Website URL":
                evidence_reference = validate_evidence_reference(evidence_url_input)
            else:
                if uploaded_evidence is None:
                    raise ValueError("Choose a local evidence file before starting CATS.")
                staged = stage_local_evidence(
                    project_root=project_root,
                    filename=uploaded_evidence.name,
                    data=uploaded_evidence.getvalue(),
                )
                evidence_reference = staged.evidence_reference

            command = build_paper_command(
                project_root=project_root,
                symbol=symbol,
                evidence_reference=evidence_reference,
                qwen_endpoint_url=qwen_endpoint,
            )

            with st.spinner("CATS evaluation cycle is running. The existing CATS authority chain remains in control..."):
                completed = subprocess.run(
                    command,
                    cwd=project_root,
                    env=os.environ.copy(),
                    capture_output=True,
                    text=True,
                    timeout=900,
                    check=False,
                )

            output = (completed.stdout or "") + ("\n" + completed.stderr if completed.stderr else "")
            st.session_state["cats_last_run_output"] = output[-12000:]
            st.session_state["cats_last_run_returncode"] = completed.returncode
            if staged is not None:
                st.session_state["cats_last_local_file"] = str(staged.original_path)

            if completed.returncode != 0:
                st.error(describe_launcher_failure(output, completed.returncode))
            else:
                st.success("CATS evaluation cycle completed. Loading the newly persisted flow...")
                st.cache_resource.clear()
                fresh_model = read_model()
                newest = fresh_model.latest_flows(limit=30)
                if newest:
                    newest_key = "flow_id" if "flow_id" in newest[0] else next(iter(newest[0]))
                    for candidate in newest:
                        candidate_id = str(candidate.get(newest_key))
                        if flow_instrument_symbol(fresh_model, candidate_id, candidate) == selected_symbol:
                            st.session_state["flow_selector"] = candidate_id
                            break
                st.rerun()
        except subprocess.TimeoutExpired:
            st.error("CATS PAPER launcher exceeded the 15-minute UI timeout. Inspect persisted state before retrying.")
        except Exception as exc:
            st.error(f"CATS PAPER run blocked: {exc}")

if st.session_state.get("cats_last_run_output"):
    rc = st.session_state.get("cats_last_run_returncode")
    with st.expander(f"Last CATS launcher output (exit code {rc})", expanded=(rc not in {0, None})):
        st.code(st.session_state["cats_last_run_output"], language="text")
    if st.session_state.get("cats_last_local_file"):
        st.caption(f"Last staged local evidence: {st.session_state['cats_last_local_file']}")

st.subheader("DB | Recent Flow History")
st.caption(f"Persisted full-flow history for the selected instrument: {selected_symbol or '—'}.")
if flows:
    st.dataframe(_operator_history_rows(flows), width="stretch", hide_index=True)
else:
    st.info(f"No persisted full-flow history is available for {selected_symbol or 'the selected instrument'}.")

st.link_button(
    "Open Alpaca PAPER",
    "https://app.alpaca.markets/account/activities",
    help="Open Alpaca account activity/order history in a new browser tab.",
)

# --- Technical detail remains available without dominating the presentation. ---
st.subheader("DB | Technical Records")
if selected_flow:
    with st.expander("Flow record"):
        st.json(selected_flow_row)

    for label, table in STAGE_TABLES:
        rows = model.rows_related_to_flow(table, selected_flow, limit=50)
        if not rows:
            continue
        with st.expander(f"{label} — {table} ({len(rows)})", expanded=False):
            st.dataframe(rows, width="stretch", hide_index=True)
            if len(rows) == 1:
                st.json(rows[0])
else:
    st.info(f"No technical records are selected because {selected_symbol or 'the selected instrument'} has no persisted full flow.")

st.caption(
    "CATS authority remains in the application and persisted domain records. "
    "Streamlit collects human run inputs, invokes the existing PAPER runtime, and reports persisted results; "
    "it does not make portfolio or execution decisions."
)
