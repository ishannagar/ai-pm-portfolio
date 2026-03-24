"""
app.py — Wealth Portfolio Advisor

Streamlit app: parse company names + share counts, resolve to NSE tickers via Claude,
fetch prices via yfinance, visualise allocation and performance, and optional
Claude-powered commentary.
"""

# Standard library
import json
import os
import re
from typing import Any, Dict, List, Optional, Tuple

# Third-party
import anthropic
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf


# Model and token budget for Claude calls
CLAUDE_MODEL = "claude-sonnet-4-5"
CLAUDE_MAX_TOKENS = 1000
CLAUDE_RESOLVE_MAX_TOKENS = 300

# Default holdings: one line per row as "Company name, shares" (resolved to .NS via Claude)
DEFAULT_COMPANY_PORTFOLIO = """Larsen and Toubro, 50
TCS, 30
Sagility, 100
Waree Energy, 25"""


def strip_code_fences(text: str) -> str:
    """Remove ``` json fences if the model wraps JSON output."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()
    return cleaned


def resolve_tickers(company_names: List[str]) -> Dict[str, str]:
    """
    Send all company names to Claude in one API call.
    Returns a dict mapping each input name (exact key from model) to an NSE Yahoo ticker (e.g. LT.NS).
    """
    if not company_names:
        return {}

    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    # Preserve order but avoid duplicate API keys in the prompt.
    unique_names: List[str] = list(dict.fromkeys(company_names))
    names_json = json.dumps(unique_names, ensure_ascii=True)

    user_prompt = f"""You map Indian company names to their primary NSE listing on Yahoo Finance.

Company names (JSON array, preserve meaning of each string):
{names_json}

Return ONLY a JSON object whose keys are EXACTLY the same strings as in the array above (character-for-character match) and whose values are Yahoo Finance tickers ending in .NS (e.g. "TCS.NS", "LT.NS").

Rules:
- Use the most liquid / common NSE symbol when ambiguous.
- Every key must be present exactly once.
- Values must be strings like "COMPANY.NS" (uppercase symbol before .NS).

Return pure JSON only, no markdown or explanation."""

    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=CLAUDE_RESOLVE_MAX_TOKENS,
        system=(
            "You resolve Indian company names to NSE Yahoo Finance tickers (.NS). "
            "Output valid JSON only."
        ),
        messages=[{"role": "user", "content": user_prompt}],
    )
    raw = response.content[0].text
    parsed = json.loads(strip_code_fences(raw))
    if not isinstance(parsed, dict):
        raise ValueError("Ticker resolution response must be a JSON object.")

    # Normalise values to uppercase NSE Yahoo tickers (.NS).
    result: Dict[str, str] = {}
    for k, v in parsed.items():
        t = str(v).strip().upper()
        if t.endswith(".BO"):
            t = t[:-3] + ".NS"
        elif not t.endswith(".NS"):
            t = f"{t}.NS"
        result[str(k).strip()] = t
    return result


def _lookup_resolved_ticker(resolved: Dict[str, str], company_name: str) -> Optional[str]:
    """Find ticker for a company line using exact or case-insensitive key match."""
    if company_name in resolved:
        return resolved[company_name]
    lower_map = {k.lower(): v for k, v in resolved.items()}
    return lower_map.get(company_name.lower().strip())


def parse_company_holdings(text: str) -> Tuple[List[Tuple[str, float]], List[str]]:
    """
    Parse sidebar text into (company_name, shares) pairs.
    Each line: "Company name, shares" — use last comma to allow commas inside names rarely.
    Returns (holdings, error_messages).
    """
    holdings: List[Tuple[str, float]] = []
    errors: List[str] = []
    for line_num, raw in enumerate(text.strip().splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "," not in line:
            errors.append(f"Line {line_num}: expected `Company name, shares` — got {raw!r}")
            continue
        name_part, shares_part = line.rsplit(",", 1)
        company_name = name_part.strip()
        shares_s = shares_part.strip()
        if not company_name:
            errors.append(f"Line {line_num}: missing company name.")
            continue
        try:
            shares = float(shares_s)
            if shares <= 0:
                errors.append(f"Line {line_num}: shares must be positive")
                continue
        except ValueError:
            errors.append(f"Line {line_num}: invalid shares {shares_s!r}")
            continue
        holdings.append((company_name, shares))
    return holdings, errors


def fetch_holding_row(ticker: str, shares: float) -> Dict[str, Any]:
    """
    Use yfinance to get latest close, 3-month history, name, and sector.
    Raises on empty history or missing price data.
    """
    stock = yf.Ticker(ticker)
    hist = stock.history(period="3mo", auto_adjust=True)
    if hist is None or hist.empty or "Close" not in hist.columns:
        raise ValueError(f"No price history for {ticker!r} (check ticker or network).")

    closes = hist["Close"].dropna()
    if closes.empty:
        raise ValueError(f"No close prices for {ticker!r}.")

    current_price = float(closes.iloc[-1])
    first_price = float(closes.iloc[0])
    if first_price <= 0:
        raise ValueError(f"Invalid starting price for {ticker!r}.")

    ret_3m_pct = (current_price / first_price - 1.0) * 100.0
    current_value = shares * current_price

    info = getattr(stock, "info", None) or {}
    company = (
        info.get("longName")
        or info.get("shortName")
        or info.get("displayName")
        or ticker
    )
    sector = info.get("sector") or info.get("category") or "—"

    return {
        "ticker": ticker,
        "company": str(company),
        "sector": str(sector),
        "shares": shares,
        "current_price": current_price,
        "current_value": current_value,
        "return_3mo_pct": ret_3m_pct,
        "_close_series": closes.rename(ticker),
    }


def build_normalized_price_df(rows: List[Dict[str, Any]]) -> pd.DataFrame:
    """
    Align all close series on dates, forward-fill gaps, normalise first row to 100.
    """
    if not rows:
        return pd.DataFrame()
    combined = pd.concat([r["_close_series"] for r in rows], axis=1)
    combined = combined.sort_index().ffill().dropna(how="all")
    if combined.empty:
        return combined
    first = combined.iloc[0]
    norm = combined.div(first, axis=1) * 100.0
    return norm


def call_claude_analysis(holdings_for_llm: List[Dict[str, Any]], total_value: float) -> str:
    """
    Send a compact portfolio summary to Claude; return plain-text analysis.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    client = anthropic.Anthropic(api_key=api_key)

    payload = {
        "total_portfolio_value_inr_approx": total_value,
        "holdings": holdings_for_llm,
    }
    user_prompt = f"""Analyse this Indian equity portfolio (values from market data).

Portfolio JSON:
{json.dumps(payload, indent=2)}

Respond in clear sections with these exact headings (markdown):

## Portfolio health summary
## Concentration risks
## Top recommendation
## Rebalancing suggestion
## Market context

Use practical, conservative language. This is educational context only, not personalised financial advice.
"""

    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=CLAUDE_MAX_TOKENS,
        system=(
            "You are a senior Indian wealth advisor. "
            "Analyse this portfolio and give practical advice."
        ),
        messages=[{"role": "user", "content": user_prompt}],
    )
    return response.content[0].text


# Streamlit page config
st.set_page_config(
    page_title="Wealth Portfolio Advisor",
    page_icon="📈",
    layout="wide",
)

st.title("📈 Wealth Portfolio Advisor")
st.caption("AI-powered portfolio analysis")

# Session defaults for caching analysis across reruns
if "company_portfolio" not in st.session_state:
    # Migrate legacy session key if present (older CSV-ticker textarea).
    st.session_state["company_portfolio"] = st.session_state.pop(
        "portfolio_csv", DEFAULT_COMPANY_PORTFOLIO
    )
if "analysis_cache" not in st.session_state:
    st.session_state["analysis_cache"] = None
if "analysis_error" not in st.session_state:
    st.session_state["analysis_error"] = None

# Sidebar: holdings input + run button
with st.sidebar:
    st.subheader("Your portfolio")
    st.caption('One line per holding: `Company name, shares` (e.g. `TCS, 30`)')
    # Bind textarea to session state so defaults persist and edits are stable across reruns.
    portfolio_text = st.text_area(
        "Holdings",
        height=220,
        key="company_portfolio",
        help="Company names are resolved to NSE Yahoo tickers (.NS) via Claude before prices load.",
    )
    analyse = st.button("Analyse Portfolio", type="primary", use_container_width=True)

if analyse:
    st.session_state["analysis_error"] = None
    st.session_state["analysis_cache"] = None

    parsed_holdings, parse_errors = parse_company_holdings(portfolio_text)
    for msg in parse_errors:
        st.warning(msg)

    if not parsed_holdings:
        st.session_state["analysis_error"] = "No valid holdings to analyse."
        st.error(st.session_state["analysis_error"])
    else:
        company_names = [name for name, _ in parsed_holdings]
        holdings: List[Tuple[str, float]] = []
        resolved_summary = ""

        try:
            if not os.environ.get("ANTHROPIC_API_KEY"):
                raise ValueError(
                    "ANTHROPIC_API_KEY is not set; cannot resolve company names to tickers."
                )

            with st.spinner("Resolving company names to NSE tickers (Claude)..."):
                resolved_map = resolve_tickers(company_names)

            resolution_errors: List[str] = []
            tickers_in_order: List[str] = []
            for company_name, shares in parsed_holdings:
                sym = _lookup_resolved_ticker(resolved_map, company_name)
                if not sym:
                    resolution_errors.append(
                        f"No ticker returned for {company_name!r}. Check Claude mapping or spelling."
                    )
                    continue
                holdings.append((sym, shares))
                tickers_in_order.append(sym)

            for msg in resolution_errors:
                st.error(msg)

            if not holdings:
                st.session_state["analysis_error"] = (
                    "Could not resolve any tickers from company names."
                )
                st.error(st.session_state["analysis_error"])
            else:
                resolved_summary = "Resolved tickers: " + ", ".join(tickers_in_order)

        except Exception as e:
            st.error(f"Ticker resolution failed: {e}")
            st.session_state["analysis_error"] = str(e)
            holdings = []

        if holdings:
            rows: List[Dict[str, Any]] = []
            fetch_errors: List[str] = []
            for ticker, shares in holdings:
                try:
                    rows.append(fetch_holding_row(ticker, shares))
                except Exception as e:
                    fetch_errors.append(f"{ticker}: {e}")

            if fetch_errors:
                for msg in fetch_errors:
                    st.error(msg)

            if not rows:
                st.session_state["analysis_error"] = "Could not load any tickers."
                st.error(st.session_state["analysis_error"])
            else:
                total_value = sum(r["current_value"] for r in rows)
                for r in rows:
                    r["allocation_pct"] = (
                        (r["current_value"] / total_value * 100.0) if total_value else 0.0
                    )

                norm_df = build_normalized_price_df(rows)
                for r in rows:
                    r.pop("_close_series", None)

                best = max(rows, key=lambda x: x["return_3mo_pct"])
                worst = min(rows, key=lambda x: x["return_3mo_pct"])

                claude_text = ""
                claude_err: Optional[str] = None
                holdings_llm = [
                    {
                        "ticker": r["ticker"],
                        "company": r["company"],
                        "sector": r["sector"],
                        "shares": r["shares"],
                        "current_price": round(r["current_price"], 2),
                        "current_value": round(r["current_value"], 2),
                        "allocation_pct": round(r["allocation_pct"], 2),
                        "return_3mo_pct": round(r["return_3mo_pct"], 2),
                    }
                    for r in rows
                ]
                try:
                    if not os.environ.get("ANTHROPIC_API_KEY"):
                        claude_err = "ANTHROPIC_API_KEY is not set; skipping AI analysis."
                    else:
                        with st.spinner("Getting AI commentary from Claude..."):
                            claude_text = call_claude_analysis(holdings_llm, total_value)
                except Exception as e:
                    claude_err = f"Claude request failed: {e}"

                st.session_state["analysis_cache"] = {
                    "rows": rows,
                    "total_value": total_value,
                    "best": best,
                    "worst": worst,
                    "norm_df": norm_df,
                    "claude_text": claude_text,
                    "claude_err": claude_err,
                    "resolved_tickers_summary": resolved_summary,
                }

# Render cached analysis if present
cache = st.session_state.get("analysis_cache")
if cache is None:
    st.info('Enter holdings in the sidebar and click **Analyse Portfolio**.')
else:
    rows = cache["rows"]
    total_value = cache["total_value"]
    best = cache["best"]
    worst = cache["worst"]
    norm_df = cache["norm_df"]

    # Let the user verify NSE symbols Claude chose before trusting charts and metrics.
    if cache.get("resolved_tickers_summary"):
        st.info(cache["resolved_tickers_summary"])

    m1, m2, m3 = st.columns(3)
    with m1:
        st.metric(
            "Total Portfolio Value",
            f"₹{total_value:,.0f}",
        )
    with m2:
        st.metric(
            "Best performer (3 months)",
            best["ticker"],
            delta=f"{best['return_3mo_pct']:.1f}%",
        )
    with m3:
        st.metric(
            "Worst performer (3 months)",
            worst["ticker"],
            delta=f"{worst['return_3mo_pct']:.1f}%",
            delta_color="inverse",
        )

    c1, c2 = st.columns(2)
    with c1:
        pie_df = pd.DataFrame(
            {
                "ticker": [r["ticker"] for r in rows],
                "value": [r["current_value"] for r in rows],
            }
        )
        fig_pie = px.pie(
            pie_df,
            names="ticker",
            values="value",
            title="Allocation by stock (by current value)",
            hole=0.35,
        )
        fig_pie.update_traces(textposition="inside", textinfo="percent+label")
        st.plotly_chart(fig_pie, use_container_width=True)

    with c2:
        if norm_df is not None and not norm_df.empty:
            fig_line = go.Figure()
            for col in norm_df.columns:
                fig_line.add_trace(
                    go.Scatter(
                        x=norm_df.index,
                        y=norm_df[col],
                        mode="lines",
                        name=str(col),
                    )
                )
            fig_line.update_layout(
                title="3-month price performance (normalised to 100)",
                xaxis_title="Date",
                yaxis_title="Indexed (start = 100)",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                margin=dict(l=40, r=40, t=60, b=40),
            )
            st.plotly_chart(fig_line, use_container_width=True)
        else:
            st.warning("Not enough history to plot normalised performance.")

    display_rows = []
    for r in rows:
        display_rows.append(
            {
                "Ticker": r["ticker"],
                "Company": r["company"],
                "Shares": r["shares"],
                "Current price": f"{r['current_price']:,.2f}",
                "Current value": f"{r['current_value']:,.0f}",
                "3M return %": f"{r['return_3mo_pct']:.2f}",
                "Allocation %": f"{r['allocation_pct']:.2f}",
            }
        )
    table_df = pd.DataFrame(display_rows)
    st.subheader("Holdings")
    st.dataframe(table_df, use_container_width=True, hide_index=True)

    st.subheader("AI analysis")
    err = cache.get("claude_err")
    if err:
        st.warning(err)
    txt = cache.get("claude_text") or ""
    if txt:
        st.info(txt)
