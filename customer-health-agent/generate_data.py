"""
generate_data.py

Generate minimal but realistic synthetic customer success data using Claude.
Outputs:
  - data/accounts.json
  - data/signals.json
"""

# Standard library imports for JSON parsing and directory creation.
import json
import os
from typing import Any

# Anthropic SDK import for calling Claude.
import anthropic


# This helper removes markdown code fences in case the model wraps JSON output.
def strip_code_fences(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()
    return cleaned


# This helper safely parses JSON and raises a clear error if parsing fails.
def parse_json(raw_text: str, label: str) -> Any:
    text = strip_code_fences(raw_text)
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON returned for {label}: {exc}") from exc


# This helper performs one Claude API call and returns the first text block.
def ask_claude(client: anthropic.Anthropic, prompt: str) -> str:
    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=600,
        system="You generate realistic synthetic enterprise customer success data. Return pure JSON only.",
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text


def main() -> None:
    # Initialize Claude client using the ANTHROPIC_API_KEY environment variable.
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    # Create output folder automatically if it does not exist.
    os.makedirs("data", exist_ok=True)

    # Prompt for accounts.json (single Claude call for this file).
    accounts_prompt = """
Generate pure JSON only.
Create a JSON array with exactly 5 enterprise account objects.
Each object must include:
id, company_name, industry, arr, csm_name, health_score, renewal_date, num_users, plan

Constraints:
- ids must be ACC-1001 to ACC-1005
- health_score is integer 1-10
- arr is annual recurring revenue in USD as an integer
- renewal_date in YYYY-MM-DD format
- realistic B2B SaaS enterprise data

Health segmentation:
- Account 1-2 (ACC-1001, ACC-1002): clearly healthy
- Account 3 (ACC-1003): mixed
- Account 4-5 (ACC-1004, ACC-1005): clearly at risk
"""
    accounts_raw = ask_claude(client, accounts_prompt)
    accounts_data = parse_json(accounts_raw, "accounts.json")

    # Prompt for signals.json (single Claude call for this file).
    signals_prompt = """
Generate pure JSON only.
Create a JSON array with exactly 5 account signal objects, one for each account_id:
ACC-1001, ACC-1002, ACC-1003, ACC-1004, ACC-1005

Each object must include:
account_id, active_users_trend, nps_score, open_tickets, days_since_csm_contact, days_to_renewal, last_login_days_ago, sentiment

Allowed values:
- active_users_trend: growing | stable | declining
- nps_score: integer 0-10
- sentiment: positive | neutral | negative | at-risk

Important rules:
- Account 1-2: clearly healthy (high NPS, growing usage, recent CSM contact)
- Account 3: mixed signals (some good some bad)
- Account 4-5: clearly at risk (low NPS, declining usage, no recent contact, renewal soon)

Use realistic numeric values and consistent account risk profile.
"""
    signals_raw = ask_claude(client, signals_prompt)
    signals_data = parse_json(signals_raw, "signals.json")

    # Save generated accounts data.
    with open("data/accounts.json", "w", encoding="utf-8") as f:
        json.dump(accounts_data, f, indent=2, ensure_ascii=True)

    # Save generated signals data.
    with open("data/signals.json", "w", encoding="utf-8") as f:
        json.dump(signals_data, f, indent=2, ensure_ascii=True)

    # Print completion message with generated file names.
    print("Synthetic customer success data generated:")
    print("- data/accounts.json")
    print("- data/signals.json")


# Run the script only when executed directly.
if __name__ == "__main__":
    main()

