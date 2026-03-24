"""
agent.py

Customer Health Intelligence Agent:
- Loads account + signal data
- Builds one combined context per account
- Uses Claude to analyze portfolio risk and account-level renewal risk
"""

# --- Standard library imports ---
# json is used to load local data files and parse model outputs.
import json
# os is used for file paths and environment variable access.
import os
# re is used for simple tokenization in keyword search.
import re
# typing helps keep function signatures explicit and readable.
from typing import Any, Dict, List

# --- Third-party import ---
# Anthropic SDK is used to call Claude for portfolio/account analysis.
import anthropic


# This constant defines the model required for all analyses.
MODEL_NAME = "claude-sonnet-4-5"

# This global store holds indexed chunks for lightweight in-memory retrieval.
_INDEXED_CHUNKS: List[Dict[str, Any]] = []


# This helper removes markdown code fences if Claude wraps JSON output.
def _strip_code_fences(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()
    return cleaned


# This helper parses JSON safely and returns fallback raw text if needed.
def _parse_json_or_fallback(text: str) -> Dict[str, Any]:
    cleaned = _strip_code_fences(text)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return {"raw_response": cleaned}


# This function loads accounts and signals JSON files from the data folder.
def load_data() -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    with open("data/accounts.json", "r", encoding="utf-8") as f:
        accounts = json.load(f)
    with open("data/signals.json", "r", encoding="utf-8") as f:
        signals = json.load(f)
    return accounts, signals


# This function combines account and signal fields into one context object per account.
def combine_account_context(accounts: List[Dict[str, Any]], signals: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    signal_by_account = {s["account_id"]: s for s in signals}
    combined: List[Dict[str, Any]] = []

    for account in accounts:
        account_id = account["id"]
        merged = {
            "account_id": account_id,
            "company_name": account.get("company_name"),
            "industry": account.get("industry"),
            "arr": account.get("arr"),
            "plan": account.get("plan"),
            "csm_name": account.get("csm_name"),
            "renewal_date": account.get("renewal_date"),
            "num_users": account.get("num_users"),
            "health_score": account.get("health_score"),
        }
        merged.update(signal_by_account.get(account_id, {}))
        combined.append(merged)

    return combined


# This function loads account + signal data and converts it into retrievable text chunks with metadata.
def load_documents() -> List[Dict[str, Any]]:
    accounts, signals = load_data()
    combined = combine_account_context(accounts, signals)
    chunks: List[Dict[str, Any]] = []

    for row in combined:
        text = (
            f"Account ID: {row.get('account_id', '')}\n"
            f"Company: {row.get('company_name', '')}\n"
            f"Industry: {row.get('industry', '')}\n"
            f"ARR: {row.get('arr', '')}\n"
            f"Plan: {row.get('plan', '')}\n"
            f"CSM: {row.get('csm_name', '')}\n"
            f"Health Score: {row.get('health_score', '')}\n"
            f"Renewal Date: {row.get('renewal_date', '')}\n"
            f"Active Users Trend: {row.get('active_users_trend', '')}\n"
            f"NPS: {row.get('nps_score', '')}\n"
            f"Open Tickets: {row.get('open_tickets', '')}\n"
            f"Days Since CSM Contact: {row.get('days_since_csm_contact', '')}\n"
            f"Days To Renewal: {row.get('days_to_renewal', '')}\n"
            f"Last Login Days Ago: {row.get('last_login_days_ago', '')}\n"
            f"Sentiment: {row.get('sentiment', '')}"
        )
        chunks.append(
            {
                "id": row.get("account_id", ""),
                "text": text,
                "source": "accounts.json + signals.json",
                "type": "account_health",
            }
        )
    return chunks


# This function builds a simple in-memory index (compatible with the Streamlit app flow).
def build_index(chunks: List[Dict[str, Any]]) -> None:
    global _INDEXED_CHUNKS
    _INDEXED_CHUNKS = list(chunks)


# This helper tokenizes text for keyword-based retrieval.
def _tokenize(text: str) -> set[str]:
    return set(re.findall(r"[a-zA-Z0-9_-]+", text.lower()))


# This function performs simple keyword search and returns top matching chunks.
def search(query: str, top_k: int = 3) -> List[Dict[str, Any]]:
    if not _INDEXED_CHUNKS:
        raise RuntimeError("Index not built. Call build_index(load_documents()) first.")

    q_tokens = _tokenize(query)
    scored: List[Dict[str, Any]] = []
    for chunk in _INDEXED_CHUNKS:
        c_tokens = _tokenize(chunk.get("text", ""))
        overlap = len(q_tokens.intersection(c_tokens))
        score = overlap / max(1, len(q_tokens))
        scored.append({**chunk, "score": round(score, 4)})

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:top_k]


# This function answers a user question using retrieved chunks plus Claude synthesis.
def answer(query: str) -> str:
    retrieved = search(query, top_k=3)
    context = "\n\n".join(
        [
            f"[Source {i}] ({c.get('id')} | {c.get('source')} | score={c.get('score')})\n{c.get('text')}"
            for i, c in enumerate(retrieved, start=1)
        ]
    )

    system_prompt = (
        "You are a senior Customer Success Intelligence assistant for enterprise SaaS. "
        "Use only the provided context to answer clearly and actionably."
    )
    user_prompt = (
        f"User question:\n{query}\n\n"
        f"Context:\n{context}\n\n"
        "Return:\n"
        "1) Direct answer\n"
        "2) Recommended next best actions\n"
        "3) Accounts/sources used"
    )
    return _ask_claude(system_prompt, user_prompt)


# This helper sends a single prompt to Claude and returns raw text.
def _ask_claude(system_prompt: str, user_prompt: str) -> str:
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    response = client.messages.create(
        model=MODEL_NAME,
        max_tokens=1000,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )
    return response.content[0].text


# This function analyzes the full portfolio in one Claude call and returns a structured response.
def analyse_portfolio() -> Dict[str, Any]:
    accounts, signals = load_data()
    combined_context = combine_account_context(accounts, signals)

    system_prompt = (
        "You are a senior Customer Success leader for an enterprise SaaS company. "
        "Analyze account portfolio risk rigorously and provide practical actions."
    )
    user_prompt = (
        "Analyze the full customer portfolio below and return JSON only.\n\n"
        "Required output schema:\n"
        "{\n"
        '  "at_risk_accounts": [\n'
        "    {\n"
        '      "account_id": "string",\n'
        '      "company_name": "string",\n'
        '      "risk_level": "high|medium|low",\n'
        '      "why_at_risk": ["string", "string"],\n'
        '      "next_best_action": "string"\n'
        "    }\n"
        "  ],\n"
        '  "portfolio_health_summary": {\n'
        '    "overall_status": "healthy|mixed|at-risk",\n'
        '    "key_themes": ["string", "string", "string"],\n'
        '    "priority_actions": ["string", "string", "string"]\n'
        "  }\n"
        "}\n\n"
        "Guidance:\n"
        "- Identify at-risk accounts based on usage trend, NPS, open tickets, recency of CSM contact, days to renewal, and sentiment.\n"
        "- Keep recommendations specific and actionable.\n\n"
        f"Portfolio data:\n{json.dumps(combined_context, indent=2)}"
    )

    raw = _ask_claude(system_prompt, user_prompt)
    return _parse_json_or_fallback(raw)


# This function analyzes one specific account deeply and returns structured renewal-risk insights.
def analyse_account(account_id: str) -> Dict[str, Any]:
    accounts, signals = load_data()
    combined_context = combine_account_context(accounts, signals)
    target = next((a for a in combined_context if a.get("account_id") == account_id), None)

    if target is None:
        return {"error": f"Account ID '{account_id}' not found in data/accounts.json or data/signals.json."}

    system_prompt = (
        "You are an expert enterprise CSM strategist preparing renewal risk briefs for leadership and account teams."
    )
    user_prompt = (
        "Analyze the account below and return JSON only.\n\n"
        "Required output schema:\n"
        "{\n"
        '  "account_id": "string",\n'
        '  "company_name": "string",\n'
        '  "risk_score": 1,\n'
        '  "churn_probability": 0,\n'
        '  "top_3_risk_signals": ["string", "string", "string"],\n'
        '  "recommended_actions": ["string", "string", "string"],\n'
        '  "renewal_call_talking_points": ["string", "string", "string"]\n'
        "}\n\n"
        "Scoring guidance:\n"
        "- risk_score is integer 1-10 where 10 is highest risk.\n"
        "- churn_probability is integer 0-100.\n"
        "- Tie every recommendation to the observed account signals.\n\n"
        f"Account data:\n{json.dumps(target, indent=2)}"
    )

    raw = _ask_claude(system_prompt, user_prompt)
    return _parse_json_or_fallback(raw)


# This helper prints dictionaries/lists in readable JSON format for local testing.
def _pretty_print(label: str, payload: Any) -> None:
    print(f"\n{label}")
    print("=" * len(label))
    print(json.dumps(payload, indent=2))


# This block tests both analyses with sample outputs when run directly.
if __name__ == "__main__":
    portfolio_result = analyse_portfolio()
    _pretty_print("Portfolio Analysis", portfolio_result)

    account_result = analyse_account("ACC-1004")
    _pretty_print("Account Analysis (ACC-1004)", account_result)

