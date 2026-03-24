"""
csmapp.py

Streamlit web app for the Customer Health Intelligence Agent.
Uses portfolio-level and per-account Claude analysis from agent.py.
"""

# Standard library: load account metadata for sidebar without extra agent calls.
import json
from pathlib import Path
from typing import Any, Dict, Optional

# Streamlit for the web UI.
import streamlit as st

# Agent functions: portfolio risk summary and single-account deep dive.
from agent import analyse_account, analyse_portfolio


# Path to bundled synthetic account data (same directory as this file).
_DATA_DIR = Path(__file__).resolve().parent / "data"
_ACCOUNTS_PATH = _DATA_DIR / "accounts.json"


def _load_accounts_for_sidebar():
    """Read accounts.json to compute total count and ARR for the sidebar."""
    if not _ACCOUNTS_PATH.exists():
        return []
    with open(_ACCOUNTS_PATH, encoding="utf-8") as f:
        return json.load(f)


def _accounts_at_risk_count(portfolio: Optional[Dict[str, Any]]) -> int:
    """
    Derive at-risk account count from cached portfolio analysis.
    Uses length of at_risk_accounts when present; otherwise 0.
    """
    if not portfolio or not isinstance(portfolio, dict):
        return 0
    items = portfolio.get("at_risk_accounts")
    if isinstance(items, list):
        return len(items)
    return 0


def _risk_badge_color(risk_level: str) -> str:
    """Map risk_level string to a human-readable badge color label for Streamlit."""
    level = (risk_level or "").lower().strip()
    if level == "high":
        return "🔴 High"
    if level == "medium":
        return "🟠 Medium"
    if level == "low":
        return "🟢 Low"
    return f"⚪ {risk_level or 'Unknown'}"


def _metric_columns_for_risk(risk_level: str):
    """
    Return border-left style hints via Streamlit container (using markdown color accent).
    Streamlit doesn't have native colored cards; we use st.metric + colored subheader text.
    """
    level = (risk_level or "").lower().strip()
    if level == "high":
        return "#c0392b"
    if level == "medium":
        return "#e67e22"
    if level == "low":
        return "#27ae60"
    return "#7f8c8d"


# Page setup: wide layout, app title in browser tab.
st.set_page_config(
    page_title="Customer Health Intelligence",
    page_icon="💚",
    layout="wide",
)

# Title and subtitle in the main header area.
st.title("💚 Customer Health Intelligence")
st.caption("AI-powered CS portfolio risk analysis")

# Session defaults so caching and UI state behave across reruns.
if "portfolio_result" not in st.session_state:
    st.session_state["portfolio_result"] = None
if "account_result" not in st.session_state:
    st.session_state["account_result"] = {}
if "last_analyzed_account_id" not in st.session_state:
    st.session_state["last_analyzed_account_id"] = None

# Load accounts once per run for sidebar metrics and account dropdown.
_accounts = _load_accounts_for_sidebar()
_total_accounts = len(_accounts)
_total_arr = sum(int(a.get("arr") or 0) for a in _accounts)
_at_risk_sidebar = _accounts_at_risk_count(st.session_state.get("portfolio_result"))

# Sidebar: portfolio-scale KPIs.
with st.sidebar:
    st.header("Portfolio snapshot")
    st.metric("Total accounts", _total_accounts)
    st.metric("Total ARR", f"${_total_arr:,.0f}" if _accounts else "—")
    st.metric(
        "Accounts at risk (from last analysis)",
        _at_risk_sidebar if st.session_state.get("portfolio_result") else "—",
        help="Run portfolio analysis in tab 1 to populate this count.",
    )

# Two main experience areas: portfolio overview vs single-account drill-down.
tab_portfolio, tab_account = st.tabs(["Portfolio View", "Account Deep Dive"])

# --- Tab 1: full-portfolio analysis and at-risk cards ---
with tab_portfolio:
    st.markdown("### Portfolio analysis")
    st.write(
        "Run a single Claude analysis across all accounts to identify at-risk customers, "
        "root causes, and next best actions."
    )

    if st.button("Run portfolio analysis", type="primary", key="btn_portfolio"):
        try:
            with st.spinner("Analyzing full portfolio with Claude..."):
                st.session_state["portfolio_result"] = analyse_portfolio()
        except Exception as e:
            st.error("Portfolio analysis failed.")
            st.exception(e)

    portfolio = st.session_state.get("portfolio_result")

    if portfolio is None:
        st.info("Click **Run portfolio analysis** to generate CS insights.")
    elif "raw_response" in portfolio and "at_risk_accounts" not in portfolio:
        st.warning("Model returned non-JSON or unexpected shape. Raw output below.")
        st.code(portfolio.get("raw_response", str(portfolio)))
    else:
        summary = portfolio.get("portfolio_health_summary") or {}
        if summary:
            st.subheader("Portfolio health summary")
            col_a, col_b = st.columns(2)
            with col_a:
                st.write("**Overall status:**", summary.get("overall_status", "—"))
            with col_b:
                themes = summary.get("key_themes") or []
                st.write("**Key themes:**")
                for t in themes:
                    st.write(f"- {t}")
            actions = summary.get("priority_actions") or []
            if actions:
                st.write("**Priority actions:**")
                for a in actions:
                    st.write(f"- {a}")

        accounts_at_risk = portfolio.get("at_risk_accounts") or []
        if not accounts_at_risk:
            st.success("No at-risk accounts listed in this analysis (or empty result).")
        else:
            st.subheader("At-risk accounts")
            for acc in accounts_at_risk:
                company = acc.get("company_name", "Unknown")
                aid = acc.get("account_id", "")
                risk = acc.get("risk_level", "")
                color_hex = _metric_columns_for_risk(risk)

                with st.container():
                    # Card-like block: title, badge, and details.
                    st.markdown(
                        f"<div style='border-left: 4px solid {color_hex}; padding-left: 12px; margin-bottom: 16px;'>"
                        f"<strong>{company}</strong> <code>{aid}</code><br/>"
                        f"<span style='color:{color_hex};font-weight:600;'>{_risk_badge_color(risk)}</span>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )
                    why = acc.get("why_at_risk") or []
                    if why:
                        st.write("**Why at risk**")
                        for w in why:
                            st.write(f"- {w}")
                    nba = acc.get("next_best_action")
                    if nba:
                        st.write("**Next best action**")
                        st.write(nba)
                    st.divider()

# --- Tab 2: pick one account and run a deep renewal-risk analysis ---
with tab_account:
    st.markdown("### Account deep dive")
    if not _accounts:
        st.error(f"No accounts found. Expected `{_ACCOUNTS_PATH}`.")
    else:
        # Build display labels: company name (human-friendly dropdown).
        name_to_id = {a.get("company_name") or a.get("id"): a.get("id") for a in _accounts}
        names = sorted(name_to_id.keys(), key=lambda x: (x or "").lower())
        selected_name = st.selectbox("Select account", names, key="select_account_name")

        if st.button("Analyze selected account", type="primary", key="btn_account"):
            account_id = name_to_id.get(selected_name)
            if not account_id:
                st.error("Could not resolve account ID.")
            else:
                try:
                    with st.spinner("Analyzing account with Claude..."):
                        st.session_state["last_analyzed_account_id"] = account_id
                        st.session_state["account_result"] = analyse_account(account_id)
                except Exception as e:
                    st.error("Account analysis failed.")
                    st.exception(e)

        result = st.session_state.get("account_result") or {}
        last_id = st.session_state.get("last_analyzed_account_id")

        if last_id and result:
            if result.get("error"):
                st.error(result["error"])
            elif "raw_response" in result and "risk_score" not in result:
                st.warning("Model returned non-JSON or unexpected shape.")
                st.code(result.get("raw_response", str(result)))
            else:
                st.subheader(result.get("company_name") or selected_name)
                st.caption(f"Account ID: `{result.get('account_id', last_id)}`")

                m1, m2 = st.columns(2)
                with m1:
                    st.metric("Risk score (1–10)", result.get("risk_score", "—"))
                with m2:
                    churn = result.get("churn_probability")
                    if churn is not None:
                        st.metric("Churn probability", f"{churn}%")
                    else:
                        st.metric("Churn probability", "—")

                signals = result.get("top_3_risk_signals") or []
                st.write("**Top risk signals**")
                for s in signals:
                    st.write(f"- {s}")

                recs = result.get("recommended_actions") or []
                st.write("**Recommended actions**")
                for r in recs:
                    st.write(f"- {r}")

                tips = result.get("renewal_call_talking_points") or []
                st.write("**Renewal call talking points**")
                for t in tips:
                    st.write(f"- {t}")
