"""
app.py

Streamlit web app for the CS Intelligence Chatbot.
It uses the `chat` function from agent.py and keeps full conversation history.
"""

# Standard library imports for loading sidebar account data.
import json
from pathlib import Path
from typing import Any, Dict, List

# Streamlit import for UI rendering.
import streamlit as st

# Import the chatbot function from the local agent module.
from agent import chat


# Load account data from local JSON for sidebar account-health cards.
DATA_PATH = Path(__file__).resolve().parent / "data" / "accounts.json"
with open(DATA_PATH, "r", encoding="utf-8") as f:
    ACCOUNTS: List[Dict[str, Any]] = json.load(f)


def health_badge(score: int) -> str:
    """
    Return a color-coded health label based on score thresholds.
    """
    if score >= 7:
        return f":green[Health Score: {score}]"
    if score >= 5:
        return f":orange[Health Score: {score}]"
    return f":red[Health Score: {score}]"


def run_chat_turn(user_message: str) -> None:
    """
    Execute one user->assistant turn and update session_state history.
    """
    with st.spinner("Agent is thinking..."):
        response_text, updated_history = chat(
            user_message,
            st.session_state["chat_history"],
        )
    st.session_state["chat_history"] = updated_history
    st.session_state["messages"] = [
        {"role": item["role"], "content": item["content"]}
        for item in updated_history
    ]


# Configure app page metadata and layout.
st.set_page_config(
    page_title="CS Intelligence Agent",
    page_icon="💬",
    layout="wide",
)

# App title and subtitle.
st.title("💬 CS Intelligence Agent")
st.caption("Ask anything about your customer accounts")

# Initialize conversation state once per user session.
if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []
if "messages" not in st.session_state:
    st.session_state["messages"] = []

# Sidebar with account cards and color-coded health scores.
with st.sidebar:
    st.header("Accounts Overview")
    for account in ACCOUNTS:
        name = account.get("company_name", "Unknown Account")
        account_id = account.get("id", "N/A")
        score = int(account.get("health_score", 0))
        with st.container(border=True):
            st.write(f"**{name}**")
            st.caption(account_id)
            st.markdown(health_badge(score))

# Suggested question buttons at top of main area.
st.markdown("### Suggested questions")
q_col1, q_col2, q_col3 = st.columns(3)

with q_col1:
    if st.button("Which accounts need attention this week?", use_container_width=True):
        run_chat_turn("Which accounts need attention this week?")

with q_col2:
    if st.button("Who is at risk of churning?", use_container_width=True):
        run_chat_turn("Who is at risk of churning?")

with q_col3:
    if st.button("Draft an email for the most at-risk account", use_container_width=True):
        run_chat_turn("Draft an email for the most at-risk account")

# Render full chat transcript using Streamlit chat bubbles.
for message in st.session_state["messages"]:
    with st.chat_message(message["role"]):
        st.write(message["content"])

# Chat input for free-form user queries.
prompt = st.chat_input("Ask about account health, churn risk, or next best actions...")
if prompt:
    # Show user bubble immediately.
    st.session_state["messages"].append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    # Get assistant response and update persistent history.
    with st.chat_message("assistant"):
        with st.spinner("Agent is thinking..."):
            response_text, updated_history = chat(prompt, st.session_state["chat_history"])
        st.write(response_text)

    st.session_state["chat_history"] = updated_history
    st.session_state["messages"] = [
        {"role": item["role"], "content": item["content"]}
        for item in updated_history
    ]

