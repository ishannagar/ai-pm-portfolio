"""
agent.py

LangGraph conversational CS Intelligence Chatbot:
- Loads account and signal data at startup
- Exposes account tools via @tool
- Uses a ReAct agent with Claude
- Provides chat(message, history) API and a CLI loop
"""

# Standard library imports for JSON loading and path handling.
import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

# LangChain/LangGraph imports for tools, messages, and agent creation.
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent


# -----------------------------
# Startup Data Loading
# -----------------------------
# Resolve file paths relative to this script so execution is stable from any cwd.
BASE_DIR = Path(__file__).resolve().parent
ACCOUNTS_PATH = BASE_DIR / "data" / "accounts.json"
SIGNALS_PATH = BASE_DIR / "data" / "signals.json"

# Load accounts and signals at startup as requested.
with open(ACCOUNTS_PATH, "r", encoding="utf-8") as f:
    ACCOUNTS: List[Dict[str, Any]] = json.load(f)

with open(SIGNALS_PATH, "r", encoding="utf-8") as f:
    SIGNALS: List[Dict[str, Any]] = json.load(f)

# Build a fast lookup for signals by account_id to simplify tool logic.
SIGNALS_BY_ACCOUNT: Dict[str, Dict[str, Any]] = {
    s.get("account_id", ""): s for s in SIGNALS
}


# -----------------------------
# Tool Definitions
# -----------------------------
@tool
def get_all_accounts() -> str:
    """
    Return a summary of all accounts with company names and health scores.
    """
    summary = [
        {
            "account_id": a.get("id"),
            "company_name": a.get("company_name"),
            "health_score": a.get("health_score"),
        }
        for a in ACCOUNTS
    ]
    return json.dumps(summary, indent=2)


@tool
def get_account_details(account_id: str) -> str:
    """
    Return full account details plus signals for one account ID.
    """
    account = next((a for a in ACCOUNTS if a.get("id") == account_id), None)
    if account is None:
        return json.dumps({"error": f"Account '{account_id}' not found."}, indent=2)

    details = {
        "account": account,
        "signals": SIGNALS_BY_ACCOUNT.get(account_id, {}),
    }
    return json.dumps(details, indent=2)


@tool
def get_at_risk_accounts() -> str:
    """
    Return accounts where health_score <= 4.
    """
    at_risk = [a for a in ACCOUNTS if (a.get("health_score") or 0) <= 4]
    return json.dumps(at_risk, indent=2)


# Bundle tools into a list used by the ReAct agent.
tools = [get_all_accounts, get_account_details, get_at_risk_accounts]


# -----------------------------
# Agent Setup
# -----------------------------
# Initialize the Anthropic chat model exactly as requested.
model = ChatAnthropic(model="claude-sonnet-4-5")

# Define the system prompt to steer CS-specific, data-backed behavior.
SYSTEM_PROMPT = (
    "You are a senior Customer Success Manager assistant. "
    "You help CSMs understand account health, identify risks, and take action. "
    "Always be specific and reference account names and data."
)

# Create a LangGraph ReAct agent with the model and tools.
agent = create_react_agent(model, tools)


# -----------------------------
# Chat API
# -----------------------------
def _history_to_messages(history: List[Dict[str, str]]) -> List[Any]:
    """
    Convert list-based history into LangChain message objects.
    Expected history format: [{"role": "user"|"assistant", "content": "..."}]
    """
    messages: List[Any] = []
    for item in history:
        role = item.get("role", "").strip().lower()
        content = item.get("content", "")
        if role == "user":
            messages.append(HumanMessage(content=content))
        elif role == "assistant":
            messages.append(AIMessage(content=content))
    return messages


def chat(message: str, history: List[Dict[str, str]]) -> Tuple[str, List[Dict[str, str]]]:
    """
    Run one conversational turn with full history and return:
    (response_text, updated_history)
    """
    # Start with system prompt, then prior history, then current user input.
    messages: List[Any] = [SystemMessage(content=SYSTEM_PROMPT)]
    messages.extend(_history_to_messages(history))
    messages.append(HumanMessage(content=message))

    # Invoke the agent with complete message state.
    result = agent.invoke({"messages": messages})

    # Read the latest assistant response from returned messages.
    response_text = "I could not generate a response."
    returned_messages = result.get("messages", [])
    for msg in reversed(returned_messages):
        if isinstance(msg, AIMessage):
            if isinstance(msg.content, str):
                response_text = msg.content
            else:
                response_text = str(msg.content)
            break

    # Append current turn to caller-managed history.
    updated_history = history + [
        {"role": "user", "content": message},
        {"role": "assistant", "content": response_text},
    ]

    return response_text, updated_history


# -----------------------------
# CLI Chat Loop
# -----------------------------
if __name__ == "__main__":
    print("CS Intelligence Agent ready. Type 'quit' to exit.")
    conversation_history: List[Dict[str, str]] = []

    while True:
        user_text = input("\nYou: ").strip()
        if user_text.lower() == "quit":
            print("Goodbye.")
            break
        if not user_text:
            continue

        reply, conversation_history = chat(user_text, conversation_history)
        print(f"\nAgent: {reply}")

