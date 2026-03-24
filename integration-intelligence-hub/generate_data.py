import json
import os
import anthropic

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

def ask_claude(prompt):
    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=800,
        system="You are an enterprise integration engineer. Return only valid JSON object, no markdown, no explanation, no code fences.",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.content[0].text.strip()

def generate_one_ticket(index):
    systems = ["Salesforce", "HubSpot", "SAP", "ServiceNow"]
    system = systems[index % len(systems)]
    raw = ask_claude(f"""Generate 1 support ticket for a {system} integration failure.
Return ONLY a JSON object with these keys:
id (string like "TKT-{1001+index}"),
title (string),
error_code (string),
system (string "{system}"),
error_message (string, max 20 words),
root_cause (string, max 20 words),
resolution_steps (array of exactly 3 short strings),
severity (string "high" or "medium" or "low"),
resolved (boolean)""")
    try:
        return json.loads(raw)
    except:
        raw = raw[raw.find('{'):raw.rfind('}')+1]
        return json.loads(raw)

def generate_one_error_code(index):
    systems = ["Salesforce", "HubSpot", "SAP", "ServiceNow"]
    system = systems[index % len(systems)]
    raw = ask_claude(f"""Generate 1 error code entry for {system}.
Return ONLY a JSON object with these keys:
code (string like "SFDC_AUTH_401"),
system (string "{system}"),
description (string, max 15 words),
common_causes (array of exactly 2 short strings),
resolution (string, max 20 words)""")
    try:
        return json.loads(raw)
    except:
        raw = raw[raw.find('{'):raw.rfind('}')+1]
        return json.loads(raw)

def main():
    os.makedirs("data", exist_ok=True)

    print("Generating support tickets...")
    tickets = []
    for i in range(5):
        print(f"  Ticket {i+1}/5...")
        tickets.append(generate_one_ticket(i))
    with open("data/support_tickets.json", "w") as f:
        json.dump(tickets, f, indent=2)
    print("support_tickets.json saved")

    print("Generating error codes...")
    codes = []
    for i in range(5):
        print(f"  Code {i+1}/5...")
        codes.append(generate_one_error_code(i))
    with open("data/error_codes.json", "w") as f:
        json.dump(codes, f, indent=2)
    print("error_codes.json saved")

    print("Generating integration docs...")
    sections = ["OAuth2 authentication errors","API rate limiting","Webhook failures","Data sync conflicts","SSL certificate issues","Timeout errors"]
    doc = "ENTERPRISE INTEGRATION TROUBLESHOOTING GUIDE\n" + "="*50 + "\n\n"
    for section in sections:
        r = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=200,
            system="Write plain text only. No markdown.",
            messages=[{"role": "user", "content": f"Write 3-4 sentences troubleshooting guide for: {section}"}]
        ).content[0].text.strip()
        doc += f"{section.upper()}\n{r}\n\n"
    with open("data/integration_docs.txt", "w") as f:
        f.write(doc)
    print("integration_docs.txt saved")

    print("\nAll data generated!")

if __name__ == "__main__":
    main()
