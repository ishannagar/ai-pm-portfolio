# Day 02 — Prompting Patterns + PRD Generator (Claude)

This folder is a compact AI PM portfolio artifact focused on **prompt engineering as product design**: how you shape model behavior, reliability, and output format for real workflows.

## What I built

- **`prompting_patterns.py`**
  - A small playground demonstrating 5 core LLM prompting patterns:
    - **System prompts**
    - **Few-shot examples**
    - **Chain-of-thought prompting** (reasoning before answering)
    - **Structured JSON output**
    - **Role + constraint prompting** (persona + strict rules)
- **`prd_generator.py`**
  - A Python **CLI tool** that:
    - takes a feature idea via `input()`
    - calls Claude (Anthropic Messages API)
    - generates a **structured PRD** with these exact sections:
      - Problem Statement
      - Target Users
      - User Stories (3)
      - Success Metrics
      - Technical Considerations
      - Risks
    - prints the PRD with clear separators
    - saves the output to `output/[feature_name].txt` (creating `output/` if needed)

## What I learned

- **Format is a feature**: a “good answer” isn’t enough—products need predictable structure for downstream workflows (eng handoff, tickets, docs).
- **Examples beat instructions**: few-shot is the fastest path to “do it like this, every time.”
- **Constraints create trust**: explicit rules (length, fields, JSON-only) reduce ambiguity and make model output usable in tooling.
- **Reasoning prompts change behavior**: for prioritization/trade-offs, getting the model to think first improves decision quality (and reveals assumptions).

## Tools used

- **Python 3**
- **Anthropic Python SDK** (`anthropic`)
- **Claude (Anthropic Messages API)**

## How to run

### Setup (once)

Install dependencies and export your API key:

```bash
pip install anthropic
export ANTHROPIC_API_KEY="your_api_key_here"
```

### Run prompting pattern demos

```bash
python prompting_patterns.py
```

You’ll see a sequence of outputs showing how each pattern changes tone, structure, and reliability.

### Run the PRD generator

```bash
python prd_generator.py
```

Then paste a feature idea when prompted. The generated PRD will be saved to `output/`.

## PM insight — why these patterns matter for AI products

In AI products, prompting patterns are **control surfaces**:

- **System + role prompts** define product voice, domain posture, and consistent decision-making.
- **Few-shot** is “UX for the model” — you’re showing the exact shape of success, not hoping the model infers it.
- **Structured output (JSON / sections)** enables automation: routing, evaluation, storage, and turning text into actions.
- **Constraints** are guardrails that reduce variance, making experiences repeatable across users and sessions.
- **Reasoning-first prompts** help with complex PM tasks (prioritization, trade-offs, risk analysis) by surfacing assumptions and decision logic.

Together, these patterns turn a chat model into a **reliable product component**—something engineering can build on and customers can trust.

