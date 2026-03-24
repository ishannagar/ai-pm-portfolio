"""
app.py

Streamlit app for an AI Loan Underwriting Assistant.
Uploads a loan application PDF, extracts text, sends it to Claude, and renders
RBI-guideline-oriented underwriting insights.
"""

# Standard library imports for JSON parsing and numeric cleanup.
import json
import re
from typing import Any, Dict

# Third-party imports for PDF extraction, UI, and Claude API.
import anthropic
import streamlit as st
from PyPDF2 import PdfReader


# Constants for model and output formatting.
MODEL_NAME = "claude-sonnet-4-5"
MAX_TOKENS = 1500


# This helper strips markdown code fences if Claude wraps JSON in ```json blocks.
def strip_code_fences(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()
    return cleaned


# This helper extracts and parses JSON, with a clear error if parsing fails.
def parse_json_response(raw_text: str) -> Dict[str, Any]:
    cleaned = strip_code_fences(raw_text)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ValueError("Claude returned non-JSON or malformed JSON.") from exc


# This helper reads all text content from the uploaded PDF using PyPDF2.
def extract_pdf_text(uploaded_file) -> str:
    reader = PdfReader(uploaded_file)
    pages_text = []
    for page in reader.pages:
        pages_text.append(page.extract_text() or "")
    return "\n".join(pages_text).strip()


# This helper sends the extracted application text to Claude for underwriting analysis.
def analyse_with_claude(application_text: str) -> Dict[str, Any]:
    client = anthropic.Anthropic()

    # System prompt defines persona, compliance constraints, and response format.
    system_prompt = (
        "You are a senior bank underwriter in India. "
        "You must perform RBI-guideline-compliant home loan analysis.\n\n"
        "Guidelines to apply:\n"
        "- FOIR (Fixed Obligations to Income Ratio) should generally be < 50%\n"
        "- LTV (Loan-to-Value) should generally be < 80% for standard approval\n"
        "- Credit score thresholds: >=750 strong, 680-749 moderate risk, <680 high risk\n\n"
        "Tasks:\n"
        "1) Extract applicant details: applicant name, monthly income, existing EMIs, credit score.\n"
        "2) Extract or infer loan amount and property value.\n"
        "3) Compute FOIR and LTV from extracted values.\n"
        "4) Return a balanced underwriting recommendation.\n\n"
        "Return ONLY valid JSON with this exact schema:\n"
        "{\n"
        '  "decision": "APPROVE|REJECT|MANUAL REVIEW",\n'
        '  "risk_score": 0,\n'
        '  "foir_calculated": 0,\n'
        '  "ltv_calculated": 0,\n'
        '  "key_strengths": ["..."],\n'
        '  "key_concerns": ["..."],\n'
        '  "missing_information": ["..."],\n'
        '  "recommended_loan_amount": 0,\n'
        '  "recommended_tenure": "...",\n'
        '  "underwriter_notes": "..."\n'
        "}\n"
        "Use integers for numeric fields where possible."
    )

    user_prompt = (
        "Analyse this home loan application text and return JSON only:\n\n"
        f"{application_text}"
    )

    response = client.messages.create(
        model=MODEL_NAME,
        max_tokens=MAX_TOKENS,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )
    return parse_json_response(response.content[0].text)


# This helper formats rupee values with Indian comma grouping for display.
def format_inr(value: Any) -> str:
    try:
        amount = int(float(str(value).replace(",", "").strip()))
    except Exception:
        return str(value)
    s = str(abs(amount))
    if len(s) <= 3:
        grouped = s
    else:
        grouped = s[-3:]
        s = s[:-3]
        while s:
            grouped = s[-2:] + "," + grouped
            s = s[:-2]
    return f"₹{grouped}" if amount >= 0 else f"-₹{grouped}"


# This helper coerces metrics into numbers safely for Streamlit metric display.
def to_number(value: Any, default: float = 0.0) -> float:
    try:
        if isinstance(value, (int, float)):
            return float(value)
        cleaned = re.sub(r"[^0-9.\-]", "", str(value))
        return float(cleaned) if cleaned else default
    except Exception:
        return default


# Configure page metadata and layout.
st.set_page_config(page_title="AI Loan Underwriting Assistant", page_icon="🏦", layout="wide")

# App title and subtitle.
st.title("🏦 AI Loan Underwriting Assistant")
st.caption("Powered by Claude — RBI guideline compliant analysis")

# Sidebar information block for user guidance and underwriting policy framing.
with st.sidebar:
    st.header("What this does")
    st.write(
        "Upload a home loan application PDF to run an AI-assisted underwriting review. "
        "The app extracts key financial indicators and returns a decision-oriented risk summary."
    )
    st.subheader("RBI Guidelines Used")
    st.write("- FOIR < 50%")
    st.write("- LTV < 80%")
    st.write("- Credit score bands: >=750 strong, 680-749 moderate, <680 high risk")

# Main upload UI controls.
uploaded_pdf = st.file_uploader("Upload loan application (PDF)", type=["pdf"])
analyse_clicked = st.button("Analyse Application", type="primary")

# Process uploaded PDF only when user explicitly clicks the analysis button.
if analyse_clicked:
    if uploaded_pdf is None:
        st.warning("Please upload a PDF file before running analysis.")
    else:
        try:
            with st.spinner("Extracting application details and running underwriting analysis..."):
                pdf_text = extract_pdf_text(uploaded_pdf)
                if not pdf_text:
                    raise ValueError("No readable text found in the uploaded PDF.")
                result = analyse_with_claude(pdf_text)

            # Normalize the decision for consistent badge rendering.
            decision = str(result.get("decision", "MANUAL REVIEW")).strip().upper()
            if decision == "APPROVE":
                st.success("### Decision: APPROVE")
            elif decision == "REJECT":
                st.error("### Decision: REJECT")
            else:
                st.warning("### Decision: MANUAL REVIEW")

            # Show key decision metrics in two-column format.
            col1, col2 = st.columns(2)
            with col1:
                st.metric("FOIR %", f"{to_number(result.get('foir_calculated'), 0):.1f}%")
            with col2:
                st.metric("Risk Score", f"{to_number(result.get('risk_score'), 0):.0f}")

            # Show strengths, concerns, and missing information in expandable sections.
            with st.expander("Key Strengths", expanded=True):
                strengths = result.get("key_strengths", [])
                if strengths:
                    for item in strengths:
                        st.markdown(f"- :green[{item}]")
                else:
                    st.write("No strengths provided.")

            with st.expander("Key Concerns", expanded=True):
                concerns = result.get("key_concerns", [])
                if concerns:
                    for item in concerns:
                        st.markdown(f"- :red[{item}]")
                else:
                    st.write("No concerns provided.")

            with st.expander("Missing Information", expanded=True):
                missing = result.get("missing_information", [])
                if missing:
                    for item in missing:
                        st.markdown(f"- :orange[{item}]")
                else:
                    st.write("No missing information reported.")

            # Render recommended loan terms in a clean table.
            st.subheader("Recommended Terms")
            terms_table = [
                {
                    "Field": "Recommended Loan Amount",
                    "Value": format_inr(result.get("recommended_loan_amount", "N/A")),
                },
                {
                    "Field": "Recommended Tenure",
                    "Value": str(result.get("recommended_tenure", "N/A")),
                },
                {
                    "Field": "LTV Calculated",
                    "Value": f"{to_number(result.get('ltv_calculated'), 0):.1f}%",
                },
            ]
            st.table(terms_table)

            # Display underwriter notes at the bottom for human review.
            st.subheader("Underwriter Notes")
            st.write(result.get("underwriter_notes", "No notes provided."))

        except Exception as exc:
            st.error("Could not process the application. Please verify the PDF and try again.")
            st.exception(exc)

