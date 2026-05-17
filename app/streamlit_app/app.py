#!/usr/bin/env python3.14
"""
Micha Stocks — Decision Dashboard
=================================
A clean, simple UI that applies Micha's reasoning framework
to help you make informed stock decisions.

For non-expert users: everything is explained in plain language.
"""

import json
import math
import os
import sqlite3
import subprocess
import sys
import tempfile
import time
from datetime import datetime

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st
import yfinance as yf

# ── Paths ──────────────────────────────────────────────────────────────

APP_DIR = os.path.dirname(__file__)
PROJECT_DIR = os.path.dirname(APP_DIR)
DB_PATH = os.path.join(PROJECT_DIR, "data", "micha.db")
OPENCODE_API = "https://opencode.ai/zen/go/v1/chat/completions"
API_KEY_ENV = "OPENCODE_GO_API_KEY"
PATTERN_EMBEDDINGS_PATH = os.path.join(PROJECT_DIR, "data", "pattern_embeddings.json")
EMBED_SCRIPT = os.path.join(PROJECT_DIR, "scripts", "embed.js")

# ── Confidence Gate (calibrated) ────────────────────────────────────
CONFIDENCE_GATE = 0.84
TOP_K_RESULTS = 5

# ── Semantically relevant threshold for guardrails ──────────────────
SEMANTIC_RELEVANCE_THRESHOLD = 0.78

# ── Audit Trail Table ───────────────────────────────────────────────

AUDIT_SCHEMA = """
CREATE TABLE IF NOT EXISTS recommendation_audit (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    query TEXT NOT NULL,
    ticker TEXT,
    recommendation TEXT,
    confidence_pct REAL,
    patterns_used TEXT,
    market_data_snapshot TEXT,
    ai_raw_output TEXT
);
"""


def init_audit_table():
    """Create the recommendation_audit table if it doesn't exist."""
    try:
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        conn = sqlite3.connect(DB_PATH)
        conn.execute(AUDIT_SCHEMA)
        conn.commit()
        conn.close()
    except Exception as e:
        st.warning(f"Could not initialize audit table: {e}")


# ── Page Config ────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Micha Stocks — Decision Tool",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Color Helpers ─────────────────────────────────────────────────────

SIGNAL_COLORS = {
    "bullish": ("🟢", "green"),
    "conditional": ("🟡", "gold"),
    "neutral": ("⚪", "gray"),
    "bearish": ("🔴", "red"),
}

def signal_color(signal):
    icon, color = SIGNAL_COLORS.get(signal, ("⚪", "gray"))
    return icon, color


# ── Semantic Search ──────────────────────────────────────────────────

@st.cache_data(ttl=300)
def load_pattern_embeddings():
    """Load pre-computed pattern embeddings (only 12 — fast)."""
    if not os.path.exists(PATTERN_EMBEDDINGS_PATH):
        return None
    with open(PATTERN_EMBEDDINGS_PATH) as f:
        return json.load(f)


def normalize(v):
    norm = math.sqrt(sum(x * x for x in v))
    return [x / norm for x in v] if norm > 0 else v


def cosine_similarity(a, b):
    return sum(x * y for x, y in zip(a, b))


def embed_query_text(text):
    """Embed a single query text via Node.js (batched for efficiency)."""
    if not os.path.exists(EMBED_SCRIPT):
        st.warning(f"Embed script not found at {EMBED_SCRIPT}")
        return None
    
    query_input = [{"id": 0, "text": text[:500]}]
    
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(query_input, f)
        tmp_input = f.name
    
    tmp_output = "/tmp/dashboard_query_embed.json"
    
    try:
        result = subprocess.run(
            ["node", EMBED_SCRIPT, tmp_input, tmp_output],
            capture_output=True, text=True, timeout=120
        )
    except FileNotFoundError:
        os.unlink(tmp_input)
        st.warning("Node.js not available for semantic search")
        return None
    finally:
        if os.path.exists(tmp_input):
            os.unlink(tmp_input)
    
    if result.returncode != 0:
        return None
    
    try:
        with open(tmp_output) as f:
            data = json.load(f)
        os.unlink(tmp_output)
        if data:
            return normalize(data[0]["embedding"])
    except (json.JSONDecodeError, KeyError, IndexError):
        pass
    return None


def semantic_pattern_search(query, top_k=5, gate=0.84):
    """Find matching patterns via semantic similarity (query → pattern embedding).
    Returns (score, pid, pattern_type) sorted by relevance.
    Gate is advisory — top_k results are always returned if available.
    Score acts as a confidence indicator in the UI.
    """
    pattern_data = load_pattern_embeddings()
    if not pattern_data:
        return []
    
    qvec = embed_query_text(query)
    if qvec is None:
        return []
    
    # Score all patterns, return top_k regardless of gate
    scored = []
    for pid, pdata in pattern_data.items():
        pvec = normalize(pdata["embedding"])
        score = cosine_similarity(qvec, pvec)
        scored.append((score, int(pid), pdata["pattern_type"]))
    
    scored.sort(reverse=True)
    return scored[:top_k]


def semantic_chunk_search(query, top_k=5, gate=0.84):
    """Find relevant transcript chunks via semantic search.
    Only used when embeddings are available (cached)."""
    embeddings_file = "/tmp/embeddings.json"
    if not os.path.exists(embeddings_file):
        return []
    
    qvec = embed_query_text(query)
    if qvec is None:
        return []
    
    try:
        with open(embeddings_file) as f:
            chunk_data = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return []
    
    # Score top chunks (optimized: we can stop early for low scores)
    scored = []
    for item in chunk_data:
        cvec = normalize(item["embedding"])
        score = cosine_similarity(qvec, cvec)
        if score >= gate:
            scored.append((score, item["id"]))
    
    scored.sort(reverse=True)
    return scored[:top_k]


@st.cache_data(ttl=60)
def search_knowledge_base(query, limit=10):
    """Search Micha's reasoning patterns from the KB.
    Uses semantic search (pre-computed embeddings) + FTS keyword fallback.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    fts_query = " OR ".join(
        f'"{w}"'
        for w in query.split()
        if len(w) > 2
        and w.lower()
        not in {"the", "and", "for", "are", "but", "not", "you", "all", "can", "has", "was", "how", "why", "what", "when"}
    )

    patterns, chunks = [], []

    # ── Try semantic search first (gives better results for natural language queries) ──
    sem_results = semantic_pattern_search(query, top_k=limit, gate=CONFIDENCE_GATE)
    if sem_results:
        # Fetch full pattern data for semantic matches
        sem_ids = [pid for _, pid, _ in sem_results]
        placeholders = ",".join("?" for _ in sem_ids)
        cur = conn.execute(
            f"""
            SELECT rp.*, '{os.path.basename(PATTERN_EMBEDDINGS_PATH)}' as video_title
            FROM reasoning_patterns rp
            WHERE rp.id IN ({placeholders})
            ORDER BY CASE rp.id
                {" ".join(f"WHEN ? THEN {i}" for i in range(len(sem_ids)))}
            END
            """,
            sem_ids + sem_ids,  # first for IN, then for ORDER BY
        )
        patterns = [dict(r) for r in cur.fetchall()]
        # Attach score
        score_map = {pid: score for score, pid, _ in sem_results}
        for p in patterns:
            p["_semantic_score"] = f"{score_map[p['id']]:.3f}"
            p["_match_method"] = "semantic"
            # Remove broken video_title override
            if p.get("video_title") == os.path.basename(PATTERN_EMBEDDINGS_PATH):
                p["video_title"] = "Micha's KB (semantic match)"

    # ── FTS pattern search (keyword fallback) ──
    if not patterns and fts_query.strip():
        try:
            # Patterns have NULL video_id, so we COALESCE for display
            cur = conn.execute(
                """
                SELECT rp.*, COALESCE(v.title, 'Micha KB') as video_title
                FROM patterns_fts fts
                JOIN reasoning_patterns rp ON fts.rowid = rp.id
                LEFT JOIN videos v ON rp.video_id = v.id
                WHERE patterns_fts MATCH ?
                ORDER BY rank
                LIMIT ?
            """,
                (fts_query, limit),
            )
            patterns = [dict(r) for r in cur.fetchall()]
            for p in patterns:
                p["_match_method"] = "keyword"
        except sqlite3.OperationalError:
            pass

    # ── FTS chunk search (exact keyword matches in transcript content) ──
    if fts_query.strip():
        try:
            cur = conn.execute(
                """
                SELECT tc.text, COALESCE(v.title, 'Micha video') as video_title, 
                       v.id as video_id
                FROM chunks_fts fts
                JOIN transcript_chunks tc ON fts.rowid = tc.id
                LEFT JOIN videos v ON tc.video_id = v.id
                WHERE chunks_fts MATCH ?
                ORDER BY rank
                LIMIT 5
            """,
                (fts_query,),
            )
            chunks = [dict(r) for r in cur.fetchall() for _ in [1]][:3]  # max 3
        except sqlite3.OperationalError:
            pass

    # ── Semantic chunk search (supplementary) ──
    if not chunks:
        try:
            # Only if embeddings are available and FTS returned nothing
            sem_chunks = semantic_chunk_search(query, top_k=3, gate=CONFIDENCE_GATE)
            if sem_chunks:
                chunk_ids = [cid for _, cid in sem_chunks if cid]
                if chunk_ids:
                    placeholders = ",".join("?" for _ in chunk_ids)
                    cur = conn.execute(
                        f"""
                        SELECT tc.text, COALESCE(v.title, 'Micha video') as video_title,
                               v.id as video_id
                        FROM transcript_chunks tc
                        LEFT JOIN videos v ON tc.video_id = v.id
                        WHERE tc.id IN ({placeholders})
                        LIMIT 3
                    """,
                        chunk_ids,
                    )
                    chunks = [dict(r) for r in cur.fetchall()]
        except Exception:
            pass

    # ── Fallback: get all patterns if nothing matched ──
    if not patterns:
        try:
            cur = conn.execute(
                """
                SELECT rp.*, COALESCE(v.title, 'Micha KB') as video_title
                FROM reasoning_patterns rp
                LEFT JOIN videos v ON rp.video_id = v.id
                ORDER BY rp.pattern_type
            """
            )
            patterns = [dict(r) for r in cur.fetchall()]
            for p in patterns:
                p["_match_method"] = "fallback"
        except sqlite3.OperationalError:
            pass

    conn.close()
    return patterns[:limit], chunks[:3]


@st.cache_data(ttl=300)
def get_all_patterns():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.execute(
        """
        SELECT rp.*, COALESCE(v.title, 'Micha KB') as video_title
        FROM reasoning_patterns rp
        LEFT JOIN videos v ON rp.video_id = v.id
        ORDER BY rp.pattern_type
    """
    )
    patterns = [dict(r) for r in cur.fetchall()]
    conn.close()
    return patterns


# ── Market Data ───────────────────────────────────────────────────────

@st.cache_data(ttl=300)
def get_stock_data(ticker):
    """Clean market data with simple explanations."""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        price = info.get("currentPrice") or info.get("regularMarketPrice") or info.get("previousClose")

        # Calculate simple explanations
        pe = info.get("trailingPE") or info.get("forwardPE")
        pe_explanation = _explain_pe(pe) if pe else "N/A"

        wk_high = info.get("fiftyTwoWeekHigh")
        wk_low = info.get("fiftyTwoWeekLow")
        range_pos = _explain_range_position(price, wk_low, wk_high) if (price and wk_low and wk_high) else "N/A"

        return {
            "ticker": ticker.upper(),
            "price": price,
            "price_change": info.get("regularMarketChange"),
            "price_change_pct": info.get("regularMarketChangePercent"),
            "pe_ratio": pe,
            "pe_explanation": pe_explanation,
            "market_cap": _format_large_number(info.get("marketCap")),
            "market_cap_raw": info.get("marketCap"),
            "52w_high": wk_high,
            "52w_low": wk_low,
            "range_position": range_pos,
            "volume": info.get("volume"),
            "avg_volume": info.get("averageVolume"),
            "volume_ratio": _calc_volume_ratio(info.get("volume"), info.get("averageVolume")),
            "dividend_yield": info.get("dividendYield"),
            "sector": info.get("sector") or "N/A",
            "industry": info.get("industry") or "N/A",
            "revenue_growth": info.get("revenueGrowth"),
            "profit_margins": info.get("profitMargins"),
            "recommendation": info.get("recommendationKey"),
            "target_mean": info.get("targetMeanPrice"),
            "target_high": info.get("targetHighPrice"),
            "target_low": info.get("targetLowPrice"),
            "description": (info.get("longBusinessSummary") or "")[:400],
            "beta": info.get("beta"),
            "short_ratio": info.get("shortRatio"),
            "forward_pe": info.get("forwardPE"),
            "earnings_growth": info.get("earningsGrowth"),
            "revenue_growth_pct": info.get("revenueGrowth"),
            "debt_to_equity": info.get("debtToEquity"),
            "current_ratio": info.get("currentRatio"),
        }
    except Exception as e:
        st.error(f"Couldn't fetch data for {ticker}: {e}")
        return {"ticker": ticker.upper(), "price": None, "error": str(e)[:200]}


def _explain_pe(pe):
    """Turn PE into simple language."""
    if pe is None:
        return "N/A"
    if pe < 0:
        return "⚠️ Company is losing money (negative earnings)"
    if pe < 10:
        return f"🟢 Low ({pe:.1f}) — could be undervalued, but check if something's wrong"
    if pe < 20:
        return f"🟢 Reasonable ({pe:.1f}) — typical for a stable company"
    if pe < 30:
        return f"🟡 Moderate ({pe:.1f}) — priced for some growth, not crazy"
    if pe < 50:
        return f"🔴 High ({pe:.1f}) — priced for strong growth, needs to deliver"
    return f"🔴 Very high ({pe:.1f}) — priced for perfection, risky if growth slows"


def _explain_range_position(price, low, high):
    """Where is the stock in its 52-week range?"""
    if not all([price, low, high]) or high == low:
        return "N/A"
    pct = (price - low) / (high - low) * 100
    if pct < 20:
        return f"🟢 Near 52-week LOW ({pct:.0f}% of range) — could be a bargain if fundamentals are solid"
    if pct < 40:
        return f"🟢 Lower end ({pct:.0f}%) — decent entry point"
    if pct < 60:
        return f"🟡 Middle of range ({pct:.0f}%) — neutral position"
    if pct < 80:
        return f"🟡 Upper end ({pct:.0f}%) — getting pricey, wait for pullback?"
    return f"🔴 Near 52-week HIGH ({pct:.0f}%) — chasing highs is risky, wait for a dip"


def _calc_volume_ratio(volume, avg_volume):
    if volume and avg_volume and avg_volume > 0:
        r = volume / avg_volume
        if r > 2:
            return f"🔴 Very high ({r:.1f}x avg) — unusual activity, something's happening"
        if r > 1.3:
            return f"🟡 Above average ({r:.1f}x avg) — elevated interest"
        return f"🟢 Normal ({r:.1f}x avg)"
    return "N/A"


def _format_large_number(n):
    if n is None:
        return "N/A"
    if n >= 1e12:
        return f"${n/1e12:.2f}T"
    if n >= 1e9:
        return f"${n/1e9:.2f}B"
    if n >= 1e6:
        return f"${n/1e6:.2f}M"
    return f"${n:,.0f}"


# ── Charts & Visualizations ─────────────────────────────────────────

def render_range_gauge(data):
    """52-week range gauge showing where price sits."""
    if not data or not all([data.get("price"), data.get("52w_low"), data.get("52w_high")]):
        return
    price = data["price"]
    low = data["52w_low"]
    high = data["52w_high"]
    if high == low:
        return
    pct = (price - low) / (high - low) * 100
    # Color based on position
    color = "#22c55e" if pct < 40 else "#f59e0b" if pct < 70 else "#ef4444"

    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=price,
        number={"suffix": "", "font": {"color": color, "size": 28}},
        title={"text": f"{data['ticker']} — 52-Week Range", "font": {"color": "#e8edf5", "size": 14}},
        delta={"reference": (high + low) / 2, "valueformat": ".2f", "increasing": {"color": "#22c55e"}, "decreasing": {"color": "#ef4444"}},
        gauge={
            "axis": {"range": [low, high], "tickcolor": "#64748b", "tickfont": {"color": "#94a3b8", "size": 10}},
            "bar": {"color": color, "thickness": 0.4},
            "steps": [
                {"range": [low, low + (high-low)*0.2], "color": "rgba(34,197,94,0.12)"},
                {"range": [low + (high-low)*0.2, low + (high-low)*0.4], "color": "rgba(34,197,94,0.07)"},
                {"range": [low + (high-low)*0.4, low + (high-low)*0.6], "color": "rgba(245,158,11,0.07)"},
                {"range": [low + (high-low)*0.6, low + (high-low)*0.8], "color": "rgba(245,158,11,0.12)"},
                {"range": [low + (high-low)*0.8, high], "color": "rgba(239,68,68,0.12)"},
            ],
            "threshold": {
                "line": {"color": "#e8edf5", "width": 2},
                "thickness": 0.6,
                "value": price,
            },
            "bgcolor": "rgba(0,0,0,0)",
        },
    ))
    fig.update_layout(
        height=220, margin=dict(l=20, r=20, t=50, b=20),
        paper_bgcolor="rgba(0,0,0,0)", font={"color": "#e8edf5"},
    )
    # Annotate range position
    zone = "Bargain zone 🟢" if pct < 20 else "Lower end 🟢" if pct < 40 else "Middle 🟡" if pct < 60 else "Upper end 🟡" if pct < 80 else "Near high 🔴"
    fig.add_annotation(text=f"{zone} ({pct:.0f}% of range)", x=0.5, y=-0.15, showarrow=False, font={"size": 12, "color": color})
    st.plotly_chart(fig, use_container_width=True, key=f"range_gauge_{data['ticker']}")


def render_pe_gauge(data):
    """PE ratio gauge showing valuation level."""
    if not data or not data.get("pe_ratio"):
        return
    pe = data["pe_ratio"]
    # Color zones
    if pe < 0:
        color, label = "#ef4444", "Negative earnings"
    elif pe < 15:
        color, label = "#22c55e", "Undervalued"
    elif pe < 25:
        color, label = "#22c55e", "Fair value"
    elif pe < 35:
        color, label = "#f59e0b", "Premium"
    elif pe < 50:
        color, label = "#f97316", "Expensive"
    else:
        color, label = "#ef4444", "Very expensive"

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=min(abs(pe), 80),
        number={"suffix": "x", "font": {"color": color, "size": 28}},
        title={"text": "PE Ratio (Valuation)", "font": {"color": "#e8edf5", "size": 14}},
        gauge={
            "axis": {"range": [0, 80], "tickvals": [0, 10, 15, 25, 35, 50, 80], "ticktext": ["0", "10", "15", "25", "35", "50", "80+"], "tickcolor": "#64748b", "tickfont": {"color": "#94a3b8", "size": 10}},
            "bar": {"color": color, "thickness": 0.4},
            "steps": [
                {"range": [0, 15], "color": "rgba(34,197,94,0.12)"},
                {"range": [15, 25], "color": "rgba(34,197,94,0.06)"},
                {"range": [25, 35], "color": "rgba(245,158,11,0.08)"},
                {"range": [35, 50], "color": "rgba(245,158,11,0.14)"},
                {"range": [50, 80], "color": "rgba(239,68,68,0.12)"},
            ],
            "threshold": {
                "line": {"color": "#e8edf5", "width": 2},
                "thickness": 0.6,
                "value": min(abs(pe), 80),
            },
            "bgcolor": "rgba(0,0,0,0)",
        },
    ))
    fig.update_layout(
        height=220, margin=dict(l=20, r=20, t=50, b=20),
        paper_bgcolor="rgba(0,0,0,0)", font={"color": "#e8edf5"},
    )
    actual_pe = f"Actual PE: {pe:.1f}x" if pe >= 0 else f"PE: {pe:.1f}x (loss-making)"
    fig.add_annotation(text=f"{label} — {actual_pe}", x=0.5, y=-0.15, showarrow=False, font={"size": 12, "color": color})
    st.plotly_chart(fig, use_container_width=True, key=f"pe_gauge_{data['ticker']}")


def render_volume_chart(data):
    """Volume comparison: current vs average."""
    if not data or not all([data.get("volume"), data.get("avg_volume")]):
        return
    vol = data["volume"]
    avg = data["avg_volume"]
    ratio = vol / avg if avg > 0 else 1

    color = "#22c55e" if ratio < 1.3 else "#f59e0b" if ratio < 2 else "#ef4444"

    fig = go.Figure()
    fig.add_bar(
        x=["Current Volume", "Avg Volume"],
        y=[vol, avg],
        marker_color=[color, "#64748b"],
        text=[f"{vol:,}", f"{avg:,}"],
        textposition="outside",
        textfont={"color": "#e8edf5", "size": 12},
        width=[0.5, 0.5],
    )
    fig.update_layout(
        title={"text": "Trading Volume", "font": {"color": "#e8edf5", "size": 14}},
        height=220, margin=dict(l=20, r=20, t=40, b=20),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "#e8edf5"},
        yaxis={"showgrid": False, "visible": False},
        xaxis={"tickfont": {"color": "#94a3b8", "size": 12}},
    )
    label = f"{ratio:.1f}x avg — Unusual activity" if ratio > 2 else f"{ratio:.1f}x avg — Elevated" if ratio > 1.3 else f"{ratio:.1f}x avg — Normal"
    fig.add_annotation(text=label, x=0.5, y=-0.22, showarrow=False, font={"size": 11, "color": color})
    st.plotly_chart(fig, use_container_width=True, key=f"volume_{data['ticker']}")


def render_financial_bars(data):
    """Key financial metrics as horizontal bars."""
    if not data:
        return
    metrics = []
    if data.get("revenue_growth") is not None:
        metrics.append(("Revenue Growth", f"{data['revenue_growth']*100:.1f}%", data["revenue_growth"], -0.5, 0.5))
    if data.get("profit_margins") is not None:
        metrics.append(("Profit Margin", f"{data['profit_margins']*100:.1f}%", data["profit_margins"], -0.3, 0.5))
    if data.get("earnings_growth") is not None:
        metrics.append(("Earnings Growth", f"{data['earnings_growth']*100:.1f}%", data["earnings_growth"], -0.5, 0.5))
    if data.get("beta") is not None:
        metrics.append(("Volatility (Beta)", f"{data['beta']:.2f}", data["beta"] / 3, 0, 1))
    if data.get("dividend_yield") is not None and data["dividend_yield"] > 0:
        dy = data["dividend_yield"]
        metrics.append(("Dividend Yield", f"{dy*100:.2f}%", dy * 20, 0, 1))

    if not metrics:
        return

    fig = go.Figure()
    for label, display, val, vmin, vmax in metrics:
        normalized = max(-1, min(1, (val - vmin) / (vmax - vmin) * 2 - 1))
        c = "#22c55e" if normalized > 0.1 else "#f59e0b" if normalized > -0.1 else "#ef4444"
        fig.add_bar(
            x=[val],
            y=[label],
            orientation="h",
            marker_color=c,
            text=display,
            textposition="outside",
            textfont={"color": "#e8edf5", "size": 11},
        )

    fig.update_layout(
        title={"text": "Key Financial Health", "font": {"color": "#e8edf5", "size": 14}},
        height=200 + 40 * len(metrics),
        margin=dict(l=10, r=10, t=40, b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "#e8edf5"},
        xaxis={"visible": False, "showgrid": False},
        yaxis={"tickfont": {"color": "#94a3b8", "size": 12}},
        showlegend=False,
        bargap=0.3,
    )
    st.plotly_chart(fig, use_container_width=True, key=f"finbars_{data['ticker']}")


def render_pattern_signal_pie(patterns):
    """Pie chart of pattern signal distribution (bullish/bearish/neutral/conditional)."""
    if not patterns:
        return
    signals = {}
    for p in patterns:
        s = p.get("confidence_signal", "neutral")
        signals[s] = signals.get(s, 0) + 1
    if not signals:
        return

    color_map = {"bullish": "#22c55e", "bearish": "#ef4444", "neutral": "#64748b", "conditional": "#f59e0b"}
    labels = [s.title() for s in signals.keys()]
    values = list(signals.values())
    colors = [color_map.get(s, "#64748b") for s in signals.keys()]

    fig = go.Figure(data=[go.Pie(
        labels=labels, values=values,
        marker={"colors": colors, "line": {"color": "#0a0e17", "width": 2}},
        textinfo="label+percent",
        textfont={"color": "#e8edf5", "size": 12},
        hoverinfo="label+value",
        hole=0.4,
    )])
    fig.update_layout(
        title={"text": "Pattern Signal Mix", "font": {"color": "#e8edf5", "size": 14}},
        height=240,
        margin=dict(l=10, r=10, t=40, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        font={"color": "#e8edf5"},
        showlegend=True,
        legend={"font": {"color": "#94a3b8", "size": 11}, "orientation": "h", "y": -0.2},
    )
    st.plotly_chart(fig, use_container_width=True, key="pattern_pie")


def render_confidence_meter(result):
    """Circular gauge showing AI confidence level."""
    if not result or not result.get("confidence_pct"):
        return
    conf = result["confidence_pct"]
    color = "#22c55e" if conf >= 75 else "#f59e0b" if conf >= 50 else "#ef4444"

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=conf,
        number={"suffix": "%", "font": {"color": color, "size": 32}},
        title={"text": "AI Confidence", "font": {"color": "#e8edf5", "size": 14}},
        gauge={
            "axis": {"range": [0, 100], "tickvals": [0, 25, 50, 75, 100], "tickfont": {"color": "#94a3b8", "size": 10}},
            "bar": {"color": color, "thickness": 0.35},
            "steps": [
                {"range": [0, 50], "color": "rgba(239,68,68,0.10)"},
                {"range": [50, 75], "color": "rgba(245,158,11,0.10)"},
                {"range": [75, 100], "color": "rgba(34,197,94,0.10)"},
            ],
            "threshold": {
                "line": {"color": "#e8edf5", "width": 2},
                "thickness": 0.55,
                "value": conf,
            },
            "bgcolor": "rgba(0,0,0,0)",
        },
    ))
    fig.update_layout(
        height=220, margin=dict(l=20, r=20, t=50, b=20),
        paper_bgcolor="rgba(0,0,0,0)", font={"color": "#e8edf5"},
    )
    label = "High confidence 🟢" if conf >= 75 else "Medium confidence 🟡" if conf >= 50 else "Low confidence 🔴"
    fig.add_annotation(text=label, x=0.5, y=-0.1, showarrow=False, font={"size": 12, "color": color})
    st.plotly_chart(fig, use_container_width=True, key="confidence_meter")


def render_pattern_score_chart(patterns):
    """Horizontal bar chart of pattern match scores."""
    scored = [p for p in patterns if p.get("_semantic_score")]
    if not scored:
        return
    scored.sort(key=lambda x: float(x["_semantic_score"]), reverse=True)

    labels = [p["pattern_type"].replace("_", " ").title()[:25] for p in scored]
    scores = [float(p["_semantic_score"]) for p in scored]
    colors = ["#22c55e" if s >= 0.84 else "#f59e0b" if s >= 0.78 else "#ef4444" for s in scores]

    fig = go.Figure()
    fig.add_bar(
        y=labels,
        x=scores,
        orientation="h",
        marker_color=colors,
        text=[f"{s:.3f}" for s in scores],
        textposition="outside",
        textfont={"color": "#e8edf5", "size": 11},
    )
    fig.add_vline(x=0.84, line_dash="dash", line_color="#22c55e", annotation_text="Gate 0.84", annotation_font={"color": "#22c55e", "size": 11})

    fig.update_layout(
        title={"text": "Pattern Match Scores", "font": {"color": "#e8edf5", "size": 14}},
        height=200 + 35 * len(scored),
        margin=dict(l=10, r=10, t=40, b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "#e8edf5"},
        xaxis={"range": [0, 1], "tickfont": {"color": "#94a3b8", "size": 10}, "gridcolor": "rgba(255,255,255,0.05)"},
        yaxis={"tickfont": {"color": "#94a3b8", "size": 11}},
        showlegend=False,
        bargap=0.3,
    )
    st.plotly_chart(fig, use_container_width=True, key="pattern_scores")


# ── PRO-GRADE VISUALIZATIONS ─────────────────────────────────────────

def render_decision_matrix(data, patterns, result):
    """Composite decision matrix — the centerpiece.
    Combines market signals + pattern signals into one actionable view.
    Inspired by Thinkorswim probability analysis + TradingView signal strength.
    """
    st.markdown("### 🎯 Decision Matrix")
    st.markdown("*At-a-glance: where the signals point*")

    # ── Compute sub-scores (0-100) ───────────────────────────────────
    tech_score = _calc_technical_score(data)
    pattern_signal_score = _calc_pattern_signal_score(patterns)
    ai_conf = result.get("confidence_pct", 50) if result else 50

    # Weighted overall
    overall = int(tech_score * 0.25 + pattern_signal_score * 0.35 + ai_conf * 0.40)

    # Determine action
    if overall >= 75:
        action, action_color, emoji = "BUY", "#22c55e", "🟢"
    elif overall >= 60:
        action, action_color, emoji = "HOLD", "#3b82f6", "🔵"
    elif overall >= 40:
        action, action_color, emoji = "WAIT", "#f59e0b", "🟡"
    else:
        action, action_color, emoji = "AVOID", "#ef4444", "🔴"

    # ── Render the dashboard ─────────────────────────────────────────
    cols = st.columns(4)

    # Column 1: Overall Score (big gauge)
    with cols[0]:
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=overall,
            number={"suffix": "", "font": {"size": 36, "color": action_color}},
            title={"text": f"{emoji} {action}", "font": {"size": 16, "color": action_color}},
            gauge={
                "axis": {"range": [0, 100], "tickvals": [0, 40, 60, 75, 100],
                         "tickfont": {"color": "#94a3b8", "size": 9}},
                "bar": {"color": action_color, "thickness": 0.3},
                "steps": [
                    {"range": [0, 40], "color": "rgba(239,68,68,0.10)"},
                    {"range": [40, 60], "color": "rgba(245,158,11,0.10)"},
                    {"range": [60, 75], "color": "rgba(59,130,246,0.10)"},
                    {"range": [75, 100], "color": "rgba(34,197,94,0.10)"},
                ],
                "threshold": {"line": {"color": "#e8edf5", "width": 2}, "thickness": 0.5, "value": overall},
                "bgcolor": "rgba(0,0,0,0)",
            },
        ))
        fig.update_layout(height=200, margin=dict(l=15, r=15, t=55, b=5),
                          paper_bgcolor="rgba(0,0,0,0)", font={"color": "#e8edf5"})
        st.plotly_chart(fig, use_container_width=True, key="decision_overall")

    # Column 2: Technical Score
    with cols[1]:
        _render_sub_gauge("📊 Technical", tech_score, data.get("ticker", ""), "tech")

    # Column 3: Pattern Signal Score
    with cols[2]:
        _render_sub_gauge("🧠 Pattern Signal", pattern_signal_score, data.get("ticker", ""), "pattern")

    # Column 4: AI Confidence
    with cols[3]:
        _render_sub_gauge("🤖 AI Reasoning", ai_conf, data.get("ticker", ""), "ai")

    # ── Breakdown details below ──────────────────────────────────────
    with st.expander("🔍 How this is calculated", expanded=False):
        st.markdown(f"""
        - **Technical Score ({tech_score:.0f}/100)**: PE ratio + 52-week range position + volume analysis
        - **Pattern Signal ({pattern_signal_score:.0f}/100)**: Quality of Micha's pattern matches + signal distribution
        - **AI Confidence ({ai_conf:.0f}/100)**: DeepSeek's self-reported confidence
        - **Overall: {overall}/100 → {action}**
        """)


def _render_sub_gauge(label, score, ticker, key_suffix):
    """Small gauge for a sub-score."""
    color = "#22c55e" if score >= 75 else "#f59e0b" if score >= 50 else "#ef4444"
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        number={"suffix": "", "font": {"size": 24, "color": color}},
        title={"text": label, "font": {"size": 12, "color": "#e8edf5"}},
        gauge={
            "axis": {"range": [0, 100], "tickvals": [0, 50, 100], "tickfont": {"color": "#94a3b8", "size": 8}},
            "bar": {"color": color, "thickness": 0.25},
            "steps": [
                {"range": [0, 50], "color": "rgba(239,68,68,0.08)"},
                {"range": [50, 75], "color": "rgba(245,158,11,0.08)"},
                {"range": [75, 100], "color": "rgba(34,197,94,0.08)"},
            ],
            "threshold": {"line": {"color": "#e8edf5", "width": 1.5}, "thickness": 0.4, "value": score},
            "bgcolor": "rgba(0,0,0,0)",
        },
    ))
    fig.update_layout(height=180, margin=dict(l=10, r=10, t=45, b=5),
                      paper_bgcolor="rgba(0,0,0,0)", font={"color": "#e8edf5"})
    st.plotly_chart(fig, use_container_width=True, key=f"subgauge_{key_suffix}_{ticker}")


def _calc_technical_score(data):
    """Score the technical health (0-100) based on PE, range, volume."""
    if not data or not data.get("price"):
        return 50
    score = 50  # start neutral

    # PE ratio
    pe = data.get("pe_ratio")
    if pe and pe > 0:
        if pe < 15: score += 20
        elif pe < 25: score += 10
        elif pe > 40: score -= 20
        elif pe > 30: score -= 10

    # Range position
    price = data.get("price")
    low = data.get("52w_low")
    high = data.get("52w_high")
    if all([price, low, high]) and high != low:
        pct = (price - low) / (high - low) * 100
        if pct < 20: score += 15
        elif pct < 40: score += 10
        elif pct > 80: score -= 15
        elif pct > 60: score -= 5

    # Volume
    vol = data.get("volume")
    avg = data.get("avg_volume")
    if vol and avg and avg > 0:
        ratio = vol / avg
        if ratio > 2: score -= 10  # unusual = risky
        elif ratio < 0.5: score -= 5  # low interest

    # Analyst target upside
    target = data.get("target_mean")
    if target and price:
        upside = (target / price - 1) * 100
        if upside > 15: score += 10
        elif upside > 5: score += 5
        elif upside < -10: score -= 10

    return max(0, min(100, score))


def _calc_pattern_signal_score(patterns):
    """Score how well the pattern signals align (0-100)."""
    if not patterns:
        return 30

    # Quality of matches
    semantic_matches = [p for p in patterns if p.get("_semantic_score")]
    if not semantic_matches:
        return 40  # fallback gets lower score

    avg_score = sum(float(p["_semantic_score"]) for p in semantic_matches) / len(semantic_matches)

    # Boost from signal distribution
    signals = [p.get("confidence_signal", "neutral") for p in patterns]
    bullish = signals.count("bullish")
    bearish = signals.count("bearish")

    base = avg_score * 100
    if bullish > bearish:
        base += 10
    elif bearish > bullish:
        base -= 10

    return max(0, min(100, base))


def render_pattern_activation_heatmap(patterns):
    """Treemap-style grid showing all patterns color-coded by match quality.
    Inspired by Finviz heatmaps — gives instant visual read of pattern coverage.
    """
    if not patterns:
        return

    # Get ALL patterns from session state for the full picture
    all_patterns = st.session_state.get("_all_patterns", patterns)

    # Build data: each pattern gets a score (semantic if available, 0 if not matched)
    matched_ids = {p["id"]: float(p.get("_semantic_score", 0)) for p in patterns if p.get("_semantic_score")}
    # For all patterns in KB
    rows = []
    signals = {"bullish": 0, "bearish": 0, "neutral": 0, "conditional": 0}
    for p in all_patterns:
        pid = p["id"]
        score = matched_ids.get(pid, 0)
        signal = p.get("confidence_signal", "neutral")
        signals[signal] = signals.get(signal, 0) + 1
        rows.append({
            "pattern": p["pattern_type"].replace("_", " ").title(),
            "score": score,
            "signal": signal,
            "matched": pid in matched_ids,
            "label": p.get("trigger_context", "")[:40],
        })

    # Sort by score descending so high matches appear first
    rows.sort(key=lambda r: r["score"], reverse=True)

    # Create a horizontal bar chart that shows ALL patterns, color-coded
    labels = [r["pattern"][:22] for r in rows]
    scores = [r["score"] for r in rows]
    colors = []
    for r in rows:
        if r["score"] >= 0.84:
            colors.append("#22c55e")  # strong match
        elif r["score"] >= 0.78:
            colors.append("#f59e0b")  # moderate
        elif r["score"] > 0:
            colors.append("#64748b")  # weak
        else:
            # Not matched — use signal color as a tint
            sig_map = {"bullish": "#22c55e", "bearish": "#ef4444", "neutral": "#64748b", "conditional": "#f59e0b"}
            base = sig_map.get(r["signal"], "#64748b")
            colors.append(base + "44")  # semi-transparent for unmatched

    fig = go.Figure()
    fig.add_bar(
        y=labels,
        x=scores,
        orientation="h",
        marker_color=colors,
        text=[f"{s:.2f}" if s > 0 else "" for s in scores],
        textposition="outside",
        textfont={"color": "#e8edf5", "size": 9},
    )
    fig.add_vline(x=0.84, line_dash="dash", line_color="#22c55e", opacity=0.5)
    fig.add_vline(x=0.78, line_dash="dot", line_color="#f59e0b", opacity=0.4)

    # Signal summary annotation
    sig_text = " | ".join(f"{k.title()}: {v}" for k, v in signals.items())
    fig.add_annotation(text=f"Signal distribution — {sig_text}",
                       x=0.5, y=-0.08, showarrow=False,
                       font={"size": 10, "color": "#94a3b8"})

    fig.update_layout(
        title={"text": "🔬 Pattern Activation Map — All 20 Patterns", "font": {"color": "#e8edf5", "size": 14}},
        height=140 + 22 * len(rows),
        margin=dict(l=10, r=60, t=40, b=40),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "#e8edf5"},
        xaxis={"range": [0, 1], "tickfont": {"color": "#94a3b8", "size": 9},
               "gridcolor": "rgba(255,255,255,0.04)"},
        yaxis={"tickfont": {"color": "#94a3b8", "size": 10}},
        showlegend=False,
        bargap=0.15,
    )
    st.plotly_chart(fig, use_container_width=True, key="activation_heatmap")


def render_audit_trail_history():
    """Timeline of past recommendations — shows what was said before.
    Inspired by TradesViz journal and trading performance dashboards.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql_query(
            """SELECT timestamp, query, ticker, recommendation, confidence_pct
               FROM recommendation_audit
               ORDER BY timestamp DESC LIMIT 50""", conn)
        conn.close()
    except Exception:
        return

    if df.empty:
        return

    st.markdown("### 📋 Audit Trail — Recommendation History")
    st.markdown("*Track what was recommended and when*")

    # Parse timestamps
    df["ts"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df = df.dropna(subset=["ts"])
    df = df.sort_values("ts")

    if len(df) < 2:
        # Just show the table
        display = df[["timestamp", "ticker", "recommendation", "confidence_pct"]].copy()
        display.columns = ["When", "Ticker", "Rec", "Conf %"]
        st.dataframe(display.tail(10), use_container_width=True, hide_index=True)
        return

    # ── Confidence trend line ────────────────────────────────────────
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["ts"], y=df["confidence_pct"],
        mode="lines+markers",
        name="AI Confidence",
        line={"color": "#3b82f6", "width": 2},
        marker={"color": df["confidence_pct"].apply(
            lambda c: "#22c55e" if c and c >= 75 else "#f59e0b" if c and c >= 50 else "#ef4444"
        ), "size": 8},
        hovertemplate="%{x|%b %d %H:%M}<br>Conf: %{y}%<extra></extra>",
    ))
    # Add recommendation labels
    for _, row in df.iterrows():
        if row.get("recommendation"):
            fig.add_annotation(
                x=row["ts"], y=row["confidence_pct"],
                text=row["recommendation"][:4],
                showarrow=False, yshift=12,
                font={"size": 9, "color": "#94a3b8"},
            )

    fig.update_layout(
        height=220,
        margin=dict(l=10, r=10, t=10, b=30),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "#e8edf5"},
        xaxis={"tickfont": {"color": "#94a3b8", "size": 10}, "gridcolor": "rgba(255,255,255,0.04)"},
        yaxis={"range": [0, 100], "tickfont": {"color": "#94a3b8", "size": 10},
               "gridcolor": "rgba(255,255,255,0.04)", "title": "Confidence %"},
        hovermode="x unified",
    )
    st.plotly_chart(fig, use_container_width=True, key="audit_history")

    # Recent table
    with st.expander("📋 View recent recommendations", expanded=False):
        display = df[["timestamp", "ticker", "recommendation", "confidence_pct", "query"]].tail(10).copy()
        display.columns = ["When", "Ticker", "Rec", "Conf %", "Query"]
        display["Query"] = display["Query"].str[:50]
        st.dataframe(display, use_container_width=True, hide_index=True)


def render_sector_peer_comparison(data):
    """Compare the stock to its sector and the broader market.
    Inspired by Finviz group analysis + Koyfin sector comparisons.
    """
    if not data or not data.get("pe_ratio") or not data.get("sector") or data["sector"] == "N/A":
        return

    st.markdown("### 🏢 Sector Context")
    st.markdown(f"*How {data.get('ticker', 'this stock')} compares to its sector peers*")

    # Fetch sector ETFs / comparison data
    sector = data["sector"]
    ticker = data.get("ticker", "")

    # Map common sectors to representative ETFs
    sector_etfs = {
        "Technology": "XLK", "Financial Services": "XLF", "Healthcare": "XLV",
        "Consumer Cyclical": "XLY", "Consumer Defensive": "XLP",
        "Industrials": "XLI", "Energy": "XLE", "Basic Materials": "XLB",
        "Utilities": "XLU", "Real Estate": "XLRE", "Communication Services": "XLC",
    }
    etf = sector_etfs.get(sector, "SPY")

    try:
        # Get sector ETF data for comparison
        etf_data = yf.Ticker(etf).info
        sector_pe = etf_data.get("trailingPE") or etf_data.get("forwardPE")
        sector_name = f"{sector} ({etf})"

        stock_pe = data["pe_ratio"]
        stock_mcap = data.get("market_cap_raw", 0)
        sector_mcap = etf_data.get("marketCap", 0)

        # Build comparison chart
        metrics = []

        # PE comparison
        if stock_pe and sector_pe:
            metrics.append(("PE Ratio", stock_pe, sector_pe, "Lower is cheaper"))

        # Market cap (normalized)
        if stock_mcap and sector_mcap and sector_mcap > 0:
            mcap_pct = (stock_mcap / sector_mcap) * 100
            metrics.append(("Weight in Sector (%)", mcap_pct, 100 / 10, "Portion of sector"))

        # Revenue growth vs sector
        stock_rev = data.get("revenue_growth")
        sector_rev = etf_data.get("revenueGrowth")
        if stock_rev is not None and sector_rev is not None:
            metrics.append(("Revenue Growth", stock_rev * 100, sector_rev * 100, "% YoY"))

        # Profit margin
        stock_margin = data.get("profit_margins")
        sector_margin = etf_data.get("profitMargins")
        if stock_margin is not None and sector_margin is not None:
            metrics.append(("Profit Margin", stock_margin * 100, sector_margin * 100, "%"))

        if not metrics:
            return

        # Grouped bar chart
        fig = go.Figure()
        labels = [m[0] for m in metrics]
        stock_vals = [m[1] for m in metrics]
        sector_vals = [m[2] for m in metrics]

        fig.add_bar(name=ticker, x=labels, y=stock_vals,
                    marker_color="#22c55e", width=0.3)
        fig.add_bar(name=sector_name, x=labels, y=sector_vals,
                    marker_color="#64748b", width=0.3)

        fig.update_layout(
            barmode="group",
            height=240,
            margin=dict(l=10, r=10, t=10, b=40),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font={"color": "#e8edf5"},
            xaxis={"tickfont": {"color": "#94a3b8", "size": 11}},
            yaxis={"tickfont": {"color": "#94a3b8", "size": 10}, "gridcolor": "rgba(255,255,255,0.04)"},
            legend={"font": {"color": "#94a3b8", "size": 11}, "orientation": "h", "y": -0.25},
        )
        st.plotly_chart(fig, use_container_width=True, key=f"sector_comp_{ticker}")

    except Exception:
        pass

def call_ai_reasoning(user_query, market_data, patterns, chunks):
    """Call DeepSeek to apply Micha's framework and get a recommendation."""
    api_key = os.environ.get(API_KEY_ENV)
    if not api_key:
        return {
            "error": f"🔑 {API_KEY_ENV} not set. Set it in your environment to get AI-powered analysis."
        }

    # Build market context (clean, simple)
    market_context = ""
    if market_data and market_data.get("price"):
        d = market_data

        # Pre-compute values to avoid backslash issues in f-strings
        div_yield = d.get("dividend_yield")
        div_str = f"{div_yield * 100:.2f}%" if div_yield else "None"

        rev_growth = d.get("revenue_growth")
        rev_str = f"{rev_growth * 100:.1f}%" if rev_growth else "N/A"

        profit_margin = d.get("profit_margins")
        profit_str = f"{profit_margin * 100:.1f}%" if profit_margin else "N/A"

        market_context = f"""## {d['ticker']} — Current Snapshot
- Price: ${d['price']:.2f}
- PE Ratio: {d['pe_ratio']:.1f} ({d.get('pe_explanation', '')})
- Market Cap: {d.get('market_cap', 'N/A')}
- 52-Week Range: ${d.get('52w_low', '?')} - ${d.get('52w_high', '?')} ({d.get('range_position', '')})
- Sector: {d.get('sector', 'N/A')}
- Volume: {d.get('volume_ratio', 'N/A')}
- Analyst Target: ${d.get('target_mean', 'N/A')} (high: ${d.get('target_high', 'N/A')}, low: ${d.get('target_low', 'N/A')})
- Dividend Yield: {div_str}
- Revenue Growth: {rev_str}
- Profit Margin: {profit_str}
- Beta (volatility): {d.get('beta', 'N/A')}
"""

    # Build KB context
    kb_context = ""
    if patterns:
        kb_context = "## Micha's Relevant Reasoning Patterns\n\n"
        for i, p in enumerate(patterns, 1):
            source = p.get('video_title', "Micha's KB")
            kb_context += f"""### {i}. {p['pattern_type'].replace('_', ' ').title()}
**When to use this:** {p['trigger_context']}
**Micha's logic:** {p['reasoning']}
**Conditions:** {p.get('conditions', 'None')}
**Signal:** {p['confidence_signal']}
**Source:** {source}

"""
    else:
        kb_context = "No specific patterns matched this query."

    if chunks:
        kb_context += "\n## Direct Quotes from Videos\n\n"
        for c in chunks:
            kb_context += f"> {c['text'][:300]}...\n> — *{c.get('video_title', 'Micha')}*\n\n"

    # ── Source citation enforcement ──────────────────────────────────
    kb_context += (
        "\n## Citation Requirements\n\n"
        "For every reasoning step, you MUST cite which pattern ID you used "
        '(e.g., "Based on pattern #15: earnings_analysis") and whether '
        "it's a direct quote or paraphrased.\n"
    )

    system_prompt = """You are a friendly stock analysis assistant applying Micha's reasoning framework from his YouTube channel (Micha Stocks).

Your job is to help a **non-expert investor** understand:
1. What the data says in plain language
2. How Micha's logic applies to this situation
3. A clear, actionable recommendation

## Output Format

Return your answer as a JSON object with these fields:
{
  "recommendation": "BUY | SELL | HOLD | WAIT | AVOID",
  "confidence": "high | medium | low",
  "confidence_pct": 75,
  "summary": "One or two sentences in plain English explaining the bottom line.",
  "reasoning_steps": [
    {
      "step": 1,
      "title": "Check valuation",
      "explanation": "Simple language explanation...",
      "pattern_used": "valuation",
      "source": "Micha's analysis on overvalued growth stocks"
    }
  ],
  "conditions_to_watch": [
    "If X happens, then Y",
    "If Z happens, then W"
  ],
  "key_numbers": [
    {"label": "PE Ratio", "value": "44.9", "verdict": "high - needs strong growth to justify"}
  ]
}

## Important rules:
- Use PLAIN LANGUAGE. No jargon without explanation.
- Every reasoning step should cite which of Micha's patterns it uses (if any).
- Be honest about uncertainty — say "Micha's framework doesn't directly address this" if needed.
- The user is NOT a financial expert. Explain like they're learning.
- Make the recommendation actionable — what should they DO?
"""

    user_prompt = f"""## User's Question
{user_query}

{market_context}

{kb_context}

## Your Task
Answer the user's question by applying Micha's reasoning framework.
Return ONLY valid JSON with the format specified."""

    try:
        resp = requests.post(
            OPENCODE_API,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "deepseek-v4-pro",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "max_tokens": 4096,
                "temperature": 0.4,
            },
            timeout=180,
        )
        data = resp.json()
        if "choices" in data:
            content = data["choices"][0]["message"].get("content", "")
            reasoning_raw = data["choices"][0]["message"].get("reasoning_content", "")

            # Try to parse JSON from the content
            try:
                # Find JSON in the response
                import re

                json_match = re.search(r"\{.*\}", content, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group())
                else:
                    result = json.loads(content)
                result["_raw_reasoning"] = reasoning_raw
                return result
            except (json.JSONDecodeError, AttributeError):
                # Return as text if JSON parsing fails
                return {"_text_output": content, "_raw_reasoning": reasoning_raw}
        else:
            return {"error": json.dumps(data, ensure_ascii=False)[:300]}
    except Exception as e:
        return {"error": f"AI call failed: {e}"}


# ── Confidence Guardrails ──────────────────────────────────────────────

def apply_confidence_guardrails(result, patterns):
    """Post-process the AI result to enforce trust & safety guardrails.

    Checks:
    - If confidence_pct < 60, prepend a warning about low confidence.
    - If patterns matched via fallback (no semantic/keyword matches),
      force-add an honesty note.
    - Ensure result dict has the guardrail fields set.
    """
    if not result or result.get("error") or result.get("_text_output"):
        return result

    # Determine if patterns are semantically relevant
    has_semantic_match = any(
        p.get("_match_method") in ("semantic", "keyword")
        and float(p.get("_semantic_score", 0) or 0) > SEMANTIC_RELEVANCE_THRESHOLD
        for p in patterns
    )
    is_fallback = all(
        p.get("_match_method") == "fallback" for p in patterns
    ) if patterns else True

    confidence_pct = result.get("confidence_pct", 0)
    summary = result.get("summary", "")

    # Low confidence warning
    if confidence_pct < 60 and confidence_pct > 0:
        warning = "⚠️ Low confidence — this is a learning tool, not advice"
        if warning not in summary:
            result["summary"] = f"{warning}. {summary}" if summary else warning

    # Fallback patterns — force honesty note
    if is_fallback:
        fallback_note = "No specific Micha patterns matched this situation — this is general analysis only"
        if fallback_note not in result.get("summary", ""):
            result["summary"] = (
                f"{result.get('summary', '')}\n\n_{fallback_note}_"
            )

    # Set guardrail metadata
    result["_guardrails_applied"] = True
    result["_guardrails_low_confidence"] = confidence_pct < 60 and confidence_pct > 0
    result["_guardrails_fallback"] = is_fallback

    return result


# ── Audit Trail ────────────────────────────────────────────────────────


def log_to_audit(query, ticker, result, patterns, market_data):
    """Log a recommendation to the recommendation_audit table."""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute(AUDIT_SCHEMA)  # ensure table exists

        # Serialize patterns used (JSON-safe)
        patterns_used = json.dumps(
            [
                {
                    "id": p.get("id"),
                    "pattern_type": p.get("pattern_type"),
                    "match_method": p.get("_match_method"),
                    "score": p.get("_semantic_score"),
                }
                for p in (patterns or [])
            ],
            ensure_ascii=False,
        )

        # Market data snapshot (safe subset)
        market_snapshot = {}
        if market_data:
            safe_keys = [
                "ticker", "price", "pe_ratio", "market_cap", "sector",
                "52w_high", "52w_low", "volume", "recommendation",
                "target_mean", "beta",
            ]
            market_snapshot = {k: market_data.get(k) for k in safe_keys if k in market_data}
        market_data_snapshot_json = json.dumps(market_snapshot, ensure_ascii=False, default=str)

        # AI raw output (strip large fields for storage efficiency)
        ai_output = {}
        if result:
            ai_output = {
                "recommendation": result.get("recommendation"),
                "confidence": result.get("confidence"),
                "confidence_pct": result.get("confidence_pct"),
                "summary": result.get("summary", "")[:500],
                "reasoning_steps_count": len(result.get("reasoning_steps", [])),
                "conditions_count": len(result.get("conditions_to_watch", [])),
                "guardrails_applied": result.get("_guardrails_applied"),
                "guardrails_low_confidence": result.get("_guardrails_low_confidence"),
                "guardrails_fallback": result.get("_guardrails_fallback"),
            }
        ai_raw_output_json = json.dumps(ai_output, ensure_ascii=False, default=str)

        conn.execute(
            """INSERT INTO recommendation_audit
               (timestamp, query, ticker, recommendation, confidence_pct,
                patterns_used, market_data_snapshot, ai_raw_output)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                datetime.utcnow().isoformat(),
                query[:500],
                ticker,
                result.get("recommendation") if result else None,
                result.get("confidence_pct") if result else None,
                patterns_used,
                market_data_snapshot_json,
                ai_raw_output_json,
            ),
        )
        conn.commit()
        conn.close()
    except Exception as e:
        # Non-blocking: audit failure should not crash the app
        print(f"Audit log error: {e}", file=sys.stderr)


# ── Simple fallback (no API key) ──────────────────────────────────────

def simple_analysis(user_query, market_data, patterns):
    """Generate a simple rule-based analysis when no AI is available."""
    ticker = market_data.get("ticker", "?")
    lines = []
    recommendations = []

    if market_data.get("pe_ratio"):
        pe = market_data["pe_ratio"]
        if pe > 40:
            lines.append(
                f"🔴 **PE is {pe:.1f}** — that's expensive. Micha says high-PE stocks need strong growth to justify the price."
            )
            recommendations.append("high_pe")
        elif pe < 15:
            lines.append(
                f"🟢 **PE is {pe:.1f}** — reasonable. This stock isn't overpriced by traditional measures."
            )
            recommendations.append("good_value")

    if market_data.get("range_position") and "Near 52-week HIGH" in market_data["range_position"]:
        lines.append(
            f"🔴 **Near 52-week high** — buying at the top is risky. Micha prefers to wait for pullbacks."
        )
        recommendations.append("near_high")
    elif market_data.get("range_position") and "Near 52-week LOW" in market_data["range_position"]:
        lines.append(
            f"🟢 **Near 52-week low** — could be a bargain if the company's fundamentals are still solid."
        )
        recommendations.append("near_low")

    if market_data.get("recommendation"):
        rec = market_data["recommendation"]
        if rec == "buy":
            lines.append(f"🟢 **Analysts say BUY** ({len(rec)} analysts) — Wall Street is bullish.")
        elif rec == "hold":
            lines.append(f"🟡 **Analysts say HOLD** — not strongly bullish or bearish.")

    # Determine overall
    if "high_pe" in recommendations and "near_high" in recommendations:
        final = "⚠️ **WAIT** — Stock is both expensive AND near its high. Wait for a pullback."
        signal = "neutral"
    elif "near_low" in recommendations and "good_value" in recommendations:
        final = "🟢 **CONSIDER BUYING** — Cheap valuation + near low. But check why it's cheap."
        signal = "bullish"
    else:
        final = "🟡 **HOLD / WATCH** — Mixed signals. Use the AI analysis for a deeper look."
        signal = "neutral"

    return {
        "summary": final,
        "reasoning_steps": [{"title": "Rule-based check", "explanation": l} for l in lines],
        "conditions_to_watch": [
            "Check the latest earnings report for forward guidance",
            "Look for insider buying/selling activity",
        ],
        "signal": signal,
        "manual": True,
    }


# ── UI Components ─────────────────────────────────────────────────────

def render_header():
    """Clean header with title and description."""
    st.markdown(
        """
    <div style="text-align: center; padding: 1rem 0 0.5rem 0;">
        <h1 style="margin: 0; font-size: 2.2rem;">📈 Micha Stocks</h1>
        <p style="color: #A0A0A0; font-size: 1.1rem; margin-top: 0.3rem;">
            Apply Micha's reasoning framework to make smarter stock decisions
        </p>
    </div>
    """,
        unsafe_allow_html=True,
    )


def render_query_box():
    """Big, clear query input."""
    col1, col2, col3 = st.columns([1, 3, 1])
    with col2:
        query = st.text_input(
            "What do you want to know?",
            value=st.session_state.get("query", ""),
            placeholder='e.g. "Should I buy NVDA right now?" or "Is AAPL a good buy at current price?"',
            label_visibility="collapsed",
        )
        col_a, col_b, col_c = st.columns([2, 1, 2])
        with col_b:
            go = st.button("🔍 Analyze", type="primary", use_container_width=True)
        return query, go


def render_basic_market_snapshot(data):
    """Simplified market snapshot for Basic mode — only the key signals."""
    if not data or data.get("error"):
        return

    st.markdown("### 📊 At a Glance")
    ticker = data.get("ticker", "?")
    price = data.get("price")
    change = data.get("price_change_pct")

    # Build signal summary
    signals = []
    pe = data.get("pe_ratio")
    if pe:
        if pe < 15: signals.append(("Valuation", "🟢 Low PE", "Looks reasonably priced"))
        elif pe < 25: signals.append(("Valuation", "🟢 Fair PE", "Typical for a stable company"))
        elif pe > 40: signals.append(("Valuation", "🔴 High PE", "Expensive — needs growth to justify"))
        elif pe > 30: signals.append(("Valuation", "🟡 Elevated PE", "Priced above average"))
        else: signals.append(("Valuation", "🟡 Moderate PE", "Acceptable"))

    low = data.get("52w_low")
    high = data.get("52w_high")
    if all([price, low, high]) and high != low:
        pct = (price - low) / (high - low) * 100
        if pct < 20: signals.append(("Price Level", "🟢 Near Low", "Could be a bargain"))
        elif pct < 40: signals.append(("Price Level", "🟢 Lower Range", "Decent entry"))
        elif pct > 80: signals.append(("Price Level", "🔴 Near High", "Chasing highs is risky"))
        elif pct > 60: signals.append(("Price Level", "🟡 Upper Range", "Getting pricey"))
        else: signals.append(("Price Level", "🟡 Mid Range", "Neutral position"))

    vol = data.get("volume")
    avg = data.get("avg_volume")
    if vol and avg and avg > 0:
        ratio = vol / avg
        if ratio > 2: signals.append(("Volume", "🔴 Unusual", "Something's happening"))
        elif ratio > 1.3: signals.append(("Volume", "🟡 Elevated", "Above average interest"))
        else: signals.append(("Volume", "🟢 Normal", "Regular activity"))

    target = data.get("target_mean")
    if target and price:
        upside = (target / price - 1) * 100
        if upside > 10: signals.append(("Analysts", "🟢 Bullish", f"{upside:.0f}% upside target"))
        elif upside < -10: signals.append(("Analysts", "🔴 Bearish", f"{upside:.0f}% downside"))
        else: signals.append(("Analysts", "🟡 Neutral", f"Target near current price"))

    # Render as cards
    cols = st.columns(4)
    with cols[0]:
        icon = "🟢" if change is not None and change >= 0 else "🔴"
        st.metric(f"{ticker} Price", f"${price:.2f}" if price else "N/A",
                  delta=f"{change:.2f}%" if change is not None else None)

    for i, (label, badge, desc) in enumerate(signals[:3]):
        with cols[i + 1]:
            st.markdown(f"**{badge}**")
            st.caption(desc)

    # One-line bottom line
    if signals:
        green = sum(1 for _, s, _ in signals if "🟢" in s)
        red = sum(1 for _, s, _ in signals if "🔴" in s)
        if green >= 3:
            st.success(f"**Bottom line:** Most signals look positive for {ticker}")
        elif red >= 2:
            st.warning(f"**Bottom line:** Several warning signs for {ticker} — proceed with caution")
        else:
            st.info(f"**Bottom line:** Mixed signals for {ticker} — see the decision matrix below")


def render_market_snapshot(data):
    """Market data in simple cards with explanations."""
    if not data or data.get("error"):
        st.warning(f"Couldn't get market data: {data.get('error', 'Unknown error')}")
        return

    st.markdown("### 📊 Market Snapshot")
    st.markdown("*Simple view of what's happening with this stock*")

    cols = st.columns(4)

    with cols[0]:
        icon = "🟢" if data.get("price_change_pct", 0) is not None and data["price_change_pct"] >= 0 else "🔴"
        st.metric(
            label=f"{data['ticker']} Price",
            value=f"${data['price']:.2f}" if data.get("price") else "N/A",
            delta=f"{data.get('price_change_pct', 0):.2f}%" if data.get("price_change_pct") is not None else None,
        )

    with cols[1]:
        icon, _ = signal_color("conditional")
        pe = data.get("pe_ratio")
        pe_label = f"{pe:.1f}" if pe else "N/A"
        st.metric(label="PE Ratio (price vs earnings)", value=pe_label)

        if data.get("pe_explanation") and "N/A" not in data["pe_explanation"]:
            st.caption(data["pe_explanation"])

    with cols[2]:
        cap = data.get("market_cap", "N/A")
        st.metric(label="Company Size (Market Cap)", value=cap)

    with cols[3]:
        target = data.get("target_mean")
        if target and data.get("price"):
            upside = (target / data["price"] - 1) * 100
            st.metric(
                label="Analyst Target",
                value=f"${target:.0f}",
                delta=f"{upside:+.1f}% vs current" if abs(upside) < 200 else None,
            )
        else:
            st.metric(label="Analyst Target", value="N/A")

    # ── Visual charts row ────────────────────────────────────────────
    st.markdown("### 📈 Visual Analysis")
    chart_cols = st.columns(2)
    with chart_cols[0]:
        render_range_gauge(data)
    with chart_cols[1]:
        render_pe_gauge(data)

    chart_cols2 = st.columns(2)
    with chart_cols2[0]:
        render_volume_chart(data)
    with chart_cols2[1]:
        render_financial_bars(data)

    # Second row — context cards
    with st.expander("📋 More details (for context)", expanded=False):
        details_cols = st.columns(3)
        items = [
            ("52-Week Range", data.get("range_position", "N/A")),
            ("Volume", data.get("volume_ratio", "N/A")),
            ("Sector / Industry", f"{data.get('sector', 'N/A')} / {data.get('industry', 'N/A')}"),
        ]
        for col, (label, val) in zip(details_cols, items):
            with col:
                st.markdown(f"**{label}**")
                st.markdown(val)

        more_items = [
            ("Revenue Growth", f"{data.get('revenue_growth', 0)*100:.1f}% YoY" if data.get("revenue_growth") else "N/A"),
            ("Profit Margin", f"{data.get('profit_margins', 0)*100:.1f}%" if data.get("profit_margins") else "N/A"),
            ("Dividend Yield", f"{data.get('dividend_yield', 0)*100:.2f}%" if data.get("dividend_yield") else "None"),
            ("Volatility (Beta)", f"{data.get('beta', 'N/A')} {'(higher risk)' if data.get('beta', 1) and data['beta'] > 1.2 else '(stable)'}" if data.get('beta') else "N/A"),
            ("Debt/Equity", f"{data.get('debt_to_equity', 'N/A')}"),
        ]
        cols2 = st.columns(3)
        for col, (label, val) in zip(cols2, more_items[:3]):
            with col:
                st.markdown(f"**{label}**")
                st.markdown(val)
        cols3 = st.columns(2)
        for col, (label, val) in zip(cols3, more_items[3:]):
            with col:
                st.markdown(f"**{label}**")
                st.markdown(val)


def render_reasoning_chain(result):
    """Show the chain of thought step by step."""
    if not result:
        return

    if result.get("_text_output"):
        st.markdown("### 🧠 Analysis")
        st.markdown(result["_text_output"])
        return

    if result.get("error"):
        st.error(result["error"])
        return

    st.markdown("### 🧠 How Micha's Logic Applies")
    st.markdown("*Here's the step-by-step thinking — each step uses a pattern from Micha's videos*")

    steps = result.get("reasoning_steps", [])
    if steps:
        for i, step in enumerate(steps):
            title = step.get("title", f"Step {i+1}")
            explanation = step.get("explanation", "")
            pattern = step.get("pattern_used", "")
            source = step.get("source", "")

            with st.container(border=True):
                cols = st.columns([0.05, 0.95])
                with cols[0]:
                    st.markdown(f"**{i+1}.**")
                with cols[1]:
                    st.markdown(f"**{title}**")
                    st.markdown(explanation)
                    if pattern:
                        icon, _ = signal_color(
                            next(
                                (
                                    p["confidence_signal"]
                                    for p in st.session_state.get("_all_patterns", [])
                                    if p["pattern_type"] == pattern
                                ),
                                "neutral",
                            )
                        )
                        st.caption(f"{icon} Pattern: *{pattern.replace('_', ' ').title()}*")
                    if source:
                        st.caption(f"📚 {source}")
    else:
        st.info("No step-by-step reasoning available.")


def render_recommendation(result):
    """Big, clear recommendation card."""
    if not result:
        return

    if result.get("_text_output"):
        return  # Already shown above

    if result.get("error"):
        return

    rec = result.get("recommendation", "N/A").upper()
    confidence = result.get("confidence", "low")
    confidence_pct = result.get("confidence_pct", 0)
    summary = result.get("summary", "")
    conditions = result.get("conditions_to_watch", [])
    key_numbers = result.get("key_numbers", [])

    # Map recommendation to color
    if rec in ("BUY", "STRONG BUY"):
        bg = "#1B5E20"
        border = "#00C853"
        emoji = "🟢"
        label = "BUY"
    elif rec in ("HOLD",):
        bg = "#1A237E"
        border = "#448AFF"
        emoji = "🔵"
        label = "HOLD"
    elif rec in ("WAIT", "WATCH"):
        bg = "#E65100"
        border = "#FFB300"
        emoji = "🟡"
        label = "WAIT"
    elif rec in ("SELL",):
        bg = "#B71C1C"
        border = "#FF1744"
        emoji = "🔴"
        label = "SELL"
    elif rec in ("AVOID",):
        bg = "#4A0000"
        border = "#D50000"
        emoji = "⛔"
        label = "AVOID"
    else:
        bg = "#263238"
        border = "#78909C"
        emoji = "⚪"
        label = rec

    # Confidence display
    if confidence_pct > 0:
        conf_display = f"{confidence_pct}%"
    else:
        conf_map = {"high": "🔷 High", "medium": "🔶 Medium", "low": "🔴 Low"}
        conf_display = conf_map.get(confidence, "Unknown")

    st.markdown("---")

    # Recommendation card
    st.markdown(
        f"""
    <div style="
        background: {bg};
        border: 2px solid {border};
        border-radius: 16px;
        padding: 1.5rem 2rem;
        margin: 0.5rem 0 1.5rem 0;
    ">
        <div style="font-size: 2rem; font-weight: bold; margin-bottom: 0.3rem;">
            {emoji} {label}
        </div>
        <div style="color: #B0B0B0; font-size: 0.9rem; margin-bottom: 0.8rem;">
            Confidence: {conf_display}
        </div>
        <div style="font-size: 1.1rem; line-height: 1.6;">
            {summary}
        </div>
    </div>
    """,
        unsafe_allow_html=True,
    )

    # Key numbers
    if key_numbers:
        st.markdown("#### 🔑 Key Numbers to Know")
        cols = st.columns(min(4, len(key_numbers)))
        for i, kn in enumerate(key_numbers):
            with cols[i % 4]:
                with st.container(border=True):
                    st.markdown(f"**{kn.get('label', '')}**")
                    st.markdown(f"**`{kn.get('value', '')}`**")
                    verdict = kn.get("verdict", "")
                    if verdict:
                        st.caption(verdict)

    # Conditions to watch
    if conditions:
        st.markdown("#### ⏳ Conditions to Watch")
        st.markdown("*These would change the recommendation — keep an eye on them*")
        for c in conditions:
            st.markdown(f"- {c}")

    # Raw reasoning (DeepSeek's chain of thought)
    if result.get("_raw_reasoning"):
        with st.expander("📖 DeepSeek's full reasoning (chain of thought)", expanded=False):
            st.markdown(result["_raw_reasoning"])


def render_kb_citations(patterns, chunks):
    """Show the KB sources that were used."""
    if not patterns and not chunks:
        return

    st.markdown("---")
    st.markdown("### 📚 Supporting Evidence from Micha's Videos")
    st.markdown("*Every claim above is based on these reasoning patterns*")

    # Patterns used
    tabs = st.tabs(["🧠 Reasoning Patterns", "💬 Direct Quotes"])

    with tabs[0]:
        for p in patterns:
            icon, color = signal_color(p["confidence_signal"])
            with st.container(border=True):
                match_badge = ""
                if p.get("_match_method") == "semantic":
                    score = p.get("_semantic_score", "")
                    match_badge = f" 🎯 Semantic match (score: {score})" if score else " 🎯 Semantic match"
                elif p.get("_match_method") == "keyword":
                    match_badge = " 🔍 Keyword match"
                
                st.markdown(f"**{icon} {p['pattern_type'].replace('_', ' ').title()}**{match_badge}")
                st.markdown(f"*When:* {p['trigger_context']}")
                st.markdown(f"*Logic:* {p['reasoning']}")
                if p.get("conditions"):
                    st.markdown(f"*Conditions:* {p['conditions']}")
                
                # Source citation — show video link if available
                video_id = p.get("video_id")
                chunk_id = p.get("chunk_id")
                if video_id and chunk_id:
                    yt_url = f"https://youtube.com/watch?v={video_id}"
                    vid_title = p.get("video_title", video_id).replace(f" [chunk_{chunk_id}]", "")
                    st.markdown(
                        f"📺 **Source:** [{vid_title[:50]}]({yt_url}) | "
                        f"`chunk #{chunk_id}`",
                        unsafe_allow_html=True
                    )
                else:
                    source_label = p.get('video_title', "Micha's KB")
                    st.caption(f"📺 Source: {source_label}")

    # Direct transcript quotes
    with tabs[1]:
        if chunks:
            for c in chunks:
                st.markdown(f"> {c['text'][:400]}...")
                st.caption(f"— *{c.get('video_title', 'Micha')}*")
                st.markdown("---")
        else:
            st.info("No direct transcript quotes matched this query. Try adding more transcripts to the KB.")


def render_kb_browser():
    """Sidebar: browse all available patterns."""
    patterns = get_all_patterns()
    if not patterns:
        st.sidebar.info("KB has no patterns yet.")
        return

    st.sidebar.markdown("### 📚 Micha's Reasoning Library")
    st.sidebar.markdown("*All patterns in the knowledge base*")
    st.sidebar.markdown("---")

    for p in patterns:
        icon, _ = signal_color(p["confidence_signal"])
        label = p["pattern_type"].replace("_", " ").title()
        with st.sidebar.expander(f"{icon} {label}", expanded=False):
            st.markdown(f"**When:** {p['trigger_context']}")
            st.markdown(f"**Logic:** {p['reasoning']}")
            if p.get("conditions"):
                st.markdown(f"**Conditions:** {p['conditions']}")
            st.caption(f"📺 {p.get('video_title', 'KB')}")


def render_mode_toggle():
    """Sidebar toggle for Basic / Pro visualization mode."""
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🎛️ Display Mode")
    mode = st.sidebar.radio(
        "Choose your view:",
        options=["Basic", "Pro"],
        index=0,
        help="Basic: bottom-line signals for quick decisions. Pro: full expert-level data.",
        label_visibility="collapsed",
    )
    st.session_state["display_mode"] = mode
    if mode == "Basic":
        st.sidebar.info(
            "**Basic mode** — clear BUY/HOLD/WAIT/AVOID signal with key numbers.\n"
            "Switch to **Pro** for the full analysis."
        )
    else:
        st.sidebar.info(
            "**Pro mode** — full expert dashboard:\n"
            "gauges, heatmaps, sector comparisons, audit trail."
        )
    return mode


def render_status_bar():
    """Show KB status."""
    patterns = get_all_patterns()
    st.sidebar.markdown("---")
    st.sidebar.markdown(f"📚 **{len(patterns)}** reasoning patterns loaded")
    if not patterns:
        st.sidebar.warning("No patterns in KB — run the scraper or seed script first.")


# ── Main App ──────────────────────────────────────────────────────────

def main():
    render_header()

    # Initialize audit trail on every run (ensures table exists)
    init_audit_table()

    # Sidebar
    render_kb_browser()
    mode = render_mode_toggle()
    render_status_bar()

    # Main area
    query, go = render_query_box()

    # Extract tickers
    if query or go:
        if not query:
            query = st.session_state.get("query", "")
        else:
            st.session_state["query"] = query

    if go or (query and st.session_state.get("auto_run", True)):
        st.session_state["auto_run"] = False

        if not query.strip():
            st.info("Type a question above and click **Analyze**")
            return

        with st.spinner("🤔 Analyzing..."):
            # 1. Detect ticker
            import re

            tickers = re.findall(r"\b[A-Z]{1,5}\b", query.upper())
            ticker = tickers[0] if tickers else None

            # 2. Fetch market data
            market_data = {}
            if ticker:
                with st.status(f"📡 Fetching data for {ticker}..."):
                    market_data = get_stock_data(ticker)

            # 3. Search KB
            with st.status("📚 Searching Micha's reasoning library..."):
                patterns, chunks = search_knowledge_base(query)
                st.session_state["_all_patterns"] = patterns

            # ── PRO: Full market snapshot with gauges ────────────────
            if mode == "Pro" and market_data and market_data.get("price"):
                render_market_snapshot(market_data)

            # ── BASIC: Simple market snapshot ────────────────────────
            if mode == "Basic" and market_data and market_data.get("price"):
                render_basic_market_snapshot(market_data)

            # 5. Generate analysis
            with st.status("🧠 Applying Micha's logic..."):
                if os.environ.get(API_KEY_ENV):
                    result = call_ai_reasoning(query, market_data, patterns, chunks)
                else:
                    result = simple_analysis(query, market_data, patterns)

                # ── Apply confidence guardrails ──────────────────────
                result = apply_confidence_guardrails(result, patterns)

            # ── Decision Matrix (both modes — the centerpiece) ─────────
            if market_data and market_data.get("price"):
                render_decision_matrix(market_data, patterns, result)

            # ── PRO: Sector Peer Comparison ────────────────────────────
            if mode == "Pro" and market_data and market_data.get("price"):
                render_sector_peer_comparison(market_data)

            # ── Regulatory Disclaimer (prominent, top of analysis) ─────
            st.markdown(
                """
            <div style="
                background: #1A1A2E;
                border: 1px solid #FF6B35;
                border-radius: 10px;
                padding: 0.8rem 1.2rem;
                margin: 0.5rem 0 1rem 0;
                font-size: 0.95rem;
            ">
                ⚠️ <strong>This is not financial advice.</strong> It's a learning tool applying
                Micha's reasoning framework. Always do your own research before investing.
            </div>
            """,
                unsafe_allow_html=True,
            )

            # ── Log to audit trail (non-blocking) ────────────────────
            log_to_audit(query, ticker, result, patterns, market_data)

            # 6. Render results
            if result:
                if isinstance(result, dict) and not result.get("error"):
                    render_recommendation(result)

                    if mode == "Basic":
                        # ── BASIC: Simple confidence + signal overview ──
                        col_signal, col_key = st.columns(2)
                        with col_signal:
                            render_confidence_meter(result)
                        with col_key:
                            render_pattern_signal_pie(patterns)

                        # Quick key numbers (inline)
                        kn = result.get("key_numbers", [])
                        if kn:
                            st.markdown("#### 🔑 Key Numbers")
                            kcols = st.columns(min(4, len(kn)))
                            for i, item in enumerate(kn):
                                with kcols[i % 4]:
                                    with st.container(border=True):
                                        st.markdown(f"**{item.get('label', '')}**")
                                        st.markdown(f"**`{item.get('value', '')}`**")
                                        if item.get("verdict"):
                                            st.caption(item["verdict"])

                    else:
                        # ── PRO: Full visualization suite ──────────────
                        viz_cols = st.columns(3)
                        with viz_cols[0]:
                            render_confidence_meter(result)
                        with viz_cols[1]:
                            render_pattern_signal_pie(patterns)
                        with viz_cols[2]:
                            render_pattern_score_chart(patterns)

                        # ── Full pattern activation heatmap ────────────
                        render_pattern_activation_heatmap(patterns)

                    # Reasoning chain (shown in both modes)
                    render_reasoning_chain(result)
                    render_kb_citations(patterns[:6], chunks)

                elif isinstance(result, dict) and result.get("error"):
                    st.error(result["error"])
                else:
                    st.markdown(result)

            # 7. Footer
            st.markdown("---")
            st.caption(
                "Powered by Micha Stocks reasoning framework"
            )

            # ── PRO only: Audit Trail History ─────────────────────────
            if mode == "Pro":
                render_audit_trail_history()

    else:
        # Show welcome / instructions
        st.markdown(
            """
        <div style="text-align: center; padding: 3rem 1rem; color: #909090;">
            <div style="font-size: 3rem; margin-bottom: 1rem;">📈</div>
            <h2>How to use this tool</h2>
            <p style="max-width: 500px; margin: 0 auto; line-height: 1.8;">
            1. <b>Type a question</b> about any stock<br>
            2. The tool <b>detects the ticker</b> automatically<br>
            3. It pulls <b>live market data</b> and <b>Micha's reasoning patterns</b><br>
            4. DeepSeek <b>applies Micha's logic</b> to your question<br>
            5. You get a <b>clear recommendation</b> with <b>sources</b>
            </p>
            <p style="margin-top: 1.5rem; font-size: 1.2rem;">
            Try: <code>"Should I buy NVDA?"</code>
            </p>
        </div>
        """,
            unsafe_allow_html=True,
        )


if __name__ == "__main__":
    main()
