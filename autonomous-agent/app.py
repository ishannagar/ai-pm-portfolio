"""
app.py

Streamlit web app for the Competitive Intelligence Agent.
Provides single-company research and multi-company comparison workflows.
"""

# Streamlit import for UI rendering.
import streamlit as st

# Import research functions from the local autonomous agent module.
from agent import compare_competitors, research_competitor


# Configure page metadata and layout.
st.set_page_config(
    page_title="Competitive Intelligence Agent",
    page_icon="🔍",
    layout="wide",
)

# App header with title/subtitle.
st.title("🔍 Competitive Intelligence Agent")
st.caption("Autonomous AI-powered competitor research")

# Cost visibility warning for users before they run analyses.
st.warning("Each research uses ~10 API calls")

# Initialize session-state cache keys once.
if "single_result" not in st.session_state:
    st.session_state["single_result"] = ""
if "compare_result" not in st.session_state:
    st.session_state["compare_result"] = ""

# Create requested tabs for single-company and multi-company flows.
tab_single, tab_compare = st.tabs(["Single Company", "Compare Companies"])


# ---------------------------------
# Tab 1: Single Company Research
# ---------------------------------
with tab_single:
    st.markdown("### Single company analysis")

    # Input for one competitor name.
    company_name = st.text_input(
        "Enter company name",
        key="single_company_input",
        placeholder="e.g., HubSpot",
    )

    # Trigger research call when button is clicked.
    if st.button("Research Competitor", type="primary", key="single_research_btn"):
        if not company_name.strip():
            st.warning("Please enter a company name.")
        else:
            try:
                # Show spinner while the autonomous agent performs web research + synthesis.
                with st.spinner("Researching competitor..."):
                    st.session_state["single_result"] = research_competitor(company_name.strip())
            except Exception as exc:
                st.error("Failed to research competitor.")
                st.exception(exc)

    # Render cached single-company result if available.
    if st.session_state.get("single_result"):
        st.info(st.session_state["single_result"])


# ---------------------------------
# Tab 2: Compare Companies
# ---------------------------------
with tab_compare:
    st.markdown("### Competitor comparison")

    # Input for comma-separated company names.
    companies_text = st.text_input(
        "Enter companies (comma separated)",
        key="compare_companies_input",
        placeholder="HubSpot, Salesforce, Freshworks",
    )

    # Trigger comparison research when button is clicked.
    if st.button("Compare Competitors", type="primary", key="compare_research_btn"):
        # Parse and clean company names from comma-separated input.
        companies = [c.strip() for c in companies_text.split(",") if c.strip()]

        if not companies:
            st.warning("Please enter at least one company.")
        else:
            try:
                # Show spinner while the agent researches and synthesizes comparison output.
                with st.spinner("Comparing competitors..."):
                    st.session_state["compare_result"] = compare_competitors(companies)
            except Exception as exc:
                st.error("Failed to compare competitors.")
                st.exception(exc)

    # Render cached comparison result if available.
    if st.session_state.get("compare_result"):
        st.info(st.session_state["compare_result"])

