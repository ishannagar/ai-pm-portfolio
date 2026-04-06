"""
agent.py

Autonomous Competitive Intelligence Agent using LangGraph ReAct.
- Uses Tavily search tools for web research
- Uses Claude for synthesis and recommendations
"""

# Standard library import for typed dictionaries/lists.
from typing import List

# LangChain/LangGraph imports for model, tools, and ReAct agent.
from langchain_anthropic import ChatAnthropic
from langchain_tavily import TavilySearch
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent


# -----------------------------
# Base Search Tool
# -----------------------------
# Tavily search instance used by all research tools.
tavily_search = TavilySearch(max_results=1)


@tool
def search_web(query: str) -> str:
    """
    Search the web with Tavily and return top results.
    """
    return str(tavily_search.invoke(query))


@tool
def get_company_info(company_name: str) -> str:
    """
    Search for company overview details:
    funding, founding year, employee count, and headquarters.
    """
    query = (
        f"{company_name} company funding founding year number of employees headquarters "
        f"official profile crunchbase wikipedia"
    )
    return str(tavily_search.invoke(query))


@tool
def get_pricing_info(company_name: str) -> str:
    """
    Search for pricing plans and product/service costs.
    """
    query = f"{company_name} pricing plans cost tiers enterprise pricing"
    return str(tavily_search.invoke(query))


@tool
def get_recent_news(company_name: str) -> str:
    """
    Search for notable news from the last 3 months.
    """
    query = f"{company_name} news last 3 months product launch funding partnership acquisition"
    return str(tavily_search.invoke(query))


# Bundle all tools for the ReAct agent.
tools = [search_web, get_company_info, get_pricing_info, get_recent_news]


# -----------------------------
# Agent Setup
# -----------------------------
# Anthropic model configuration with requested token budget.
model = ChatAnthropic(model="claude-sonnet-4-5", max_tokens=400)

# System prompt to position the model as a senior CI analyst.
SYSTEM_PROMPT = (
    "You are a senior competitive intelligence analyst. "
    "You produce clear, decision-ready competitor research for product and GTM leaders. "
    "Use tools to gather current evidence, cite key facts directly, and avoid speculation. "
    "Highlight confidence and data gaps when information is incomplete."
)

# Create LangGraph ReAct agent.
agent = create_react_agent(model, tools)


# -----------------------------
# Core Functions
# -----------------------------
def _invoke_agent(user_task: str) -> str:
    """
    Helper to invoke the ReAct agent and return final assistant text.
    """
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=user_task),
    ]
    result = agent.invoke({"messages": messages})

    # Extract last assistant message from returned message list.
    final_text = "No analysis generated."
    for msg in reversed(result.get("messages", [])):
        if isinstance(msg, AIMessage):
            final_text = msg.content if isinstance(msg.content, str) else str(msg.content)
            break
    return final_text


def research_competitor(company_name: str) -> str:
    """
    Research one competitor and return a structured analysis string.
    """
    task = (
        f"Research {company_name} as a competitor. "
        f"Find: overview, pricing, key features, strengths, weaknesses, recent news.\n\n"
        f"Output format (keep each section to 1 bullet points max):\n"
        f"1) Overview (founding, size, positioning)\n"
        f"2) Pricing (one line summary)\n"
        f"3) Top 1 strengths\n"
        f"4) Top 1 weaknesses\n"
        f"5) One recent news item\n"
        f"Keep total response under 50 words.\n"
    )
    return _invoke_agent(task)


def compare_competitors(companies: List[str]) -> str:
    """
    Research each competitor, then return a comparison table and recommendation.
    """
    if not companies:
        return "No competitors provided."

    # First, gather individual research summaries.
    per_company_summaries = []
    for company in companies:
        summary = research_competitor(company)
        per_company_summaries.append({"company": company, "summary": summary})

    # Then ask the agent to synthesize a head-to-head comparison and recommendation.
    comparison_task = (
        "You are given competitor research summaries.\n\n"
        f"Competitor summaries:\n{per_company_summaries}\n\n"
        "Create:\n"
        "- A concise markdown comparison table with columns: "
        "Company | Positioning | Pricing posture | Top strengths | Top weaknesses | Momentum signal\n"
        "- A recommendation section with:\n"
        "  1) Who is the strongest competitor and why\n"
        "  2) Biggest market risk for us\n"
        "  3) 1 actionable responses (product, pricing, GTM)\n"
    )
    return _invoke_agent(comparison_task)


# -----------------------------
# CLI Test Run
# -----------------------------
if __name__ == "__main__":
    test_companies = ["Gainsight", "EvoluteIQ"]

    print("=== Individual Research ===\n")
    for c in test_companies:
        print(f"\n--- {c} ---")
        print(research_competitor(c))

    print("\n\n=== Comparison & Recommendation ===\n")
    print(compare_competitors(test_companies))

