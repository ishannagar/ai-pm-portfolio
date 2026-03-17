import anthropic
client = anthropic.Anthropic()

# PATTERN 5: Role + Constraint — most powerful pattern for consistent output
# Combine WHO Claude is + WHAT rules it must follow
# Use this for: any tool you're building for repeated use

import anthropic
client = anthropic.Anthropic()

response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=500,
    system='You are a senior Product Manager at a B2B SaaS company with 10 years experience. You give concise, opinionated answers focused on business impact.',
    messages=[
        {
            "role": "user",
            "content": "Should we build a mobile app or focus on our web product first?"
        }
    ]
)

print("PATTERN 1 — System Prompt:")
print(response.content[0].text)
print("\n" + "="*50 + "\n")

# PATTERN 2: Few-shot examples — show Claude the format you want
# Instead of describing the format, you show it 1-2 examples
# Claude matches the pattern exactly

response2 = client.messages.create(
    model="claude-sonnet-4-5",
    max_tokens=500,
    system="You are a senior Product Manager who writes crisp user stories.",
    messages=[
        {
            "role": "user",
            # We show Claude 2 examples THEN ask for our real one
            "content": """Here are examples of well-written user stories:

Example 1:
Feature: Password reset
User story: As a user who forgot my password, I want to reset it via email so that I can regain access to my account within 2 minutes.
Acceptance criteria: Email arrives within 60 seconds, link expires in 1 hour, password must meet security requirements.

Example 2:
Feature: Export to CSV
User story: As a finance manager, I want to export transaction data to CSV so that I can analyse it in Excel without manual data entry.
Acceptance criteria: Export includes all columns, handles up to 10k rows, filename includes date.

Now write a user story for:
Feature: AI invoice scanner"""
        }
    ]
)

print("PATTERN 2 — Few-shot examples:")
print(response2.content[0].text)
print("\n" + "="*50 + "\n")



# PATTERN 3: Chain of Thought — forces Claude to reason before answering
# Magic phrase: "Think step by step"
# Use this for: prioritisation, trade-off decisions, complex analysis

response3 = client.messages.create(
    model="claude-sonnet-4-5",
    max_tokens=800,
    system="You are a senior Product Manager.",
    messages=[
        {
            "role": "user",
            "content": """Think step by step before answering.

We have 3 features to prioritise for next quarter:
1. SSO integration — requested by 5 enterprise customers
2. Mobile app — requested by 40% of users in survey
3. API rate limiting — needed for platform stability

We are a B2B SaaS company, 80% enterprise customers, Series B, 
team of 3 engineers available.

Which should we build first and why?"""
        }
    ]
)

print("PATTERN 3 — Chain of Thought:")
print(response3.content[0].text)
print("\n" + "="*50 + "\n")

response4 = client.messages.create(
    model="claude-sonnet-4-5",
    max_tokens=800,
    system="""You are a senior Product Manager. 
You always respond with valid JSON only — no extra text, no markdown, no explanation.
Just the raw JSON object.""",
    messages=[
        {
            "role": "user",
            "content": """Analyse this feature request and return a JSON object with exactly these fields:
{
    "feature_name": "string",
    "problem_statement": "string — 1 sentence",
    "target_user": "string",
    "business_value": "string — 1 sentence",
    "complexity": "low/medium/high",
    "recommended_priority": "p0/p1/p2",
    "risks": ["risk1", "risk2"]
}

Feature request: AI-powered invoice scanner that extracts line items and detects anomalies"""
        }
    ]
)

print("PATTERN 4 — Structured JSON output:")
print(response4.content[0].text)
print("\n" + "="*50 + "\n")
response5 = client.messages.create(
    model="claude-sonnet-4-5",
    max_tokens=500,
    system="""You are a brutal but fair product critic with 15 years experience 
at top tech companies. 

Your rules:
- Maximum 3 sentences per point
- Always include one thing that could kill the product
- Never be diplomatic — be honest
- End with a single verdict: SHIP IT / KILL IT / NEEDS WORK""",
    messages=[
        {
            "role": "user",
            "content": "Review this product idea: A WhatsApp bot that helps small Indian businesses manage their inventory using voice messages in Hindi"
        }
    ]
)

print("PATTERN 5 — Role + Constraint:")
print(response5.content[0].text)
print("\n" + "="*50 + "\n")
