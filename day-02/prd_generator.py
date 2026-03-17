"""
prd_generator.py

A small CLI tool that turns a feature idea into a structured PRD using the Anthropic Claude API.
"""

# --- Imports (standard library) ---
# We use os for environment variables and creating folders.
import os
# We use re to create a safe filename from the feature name.
import re
# We use textwrap to keep the system prompt readable in code.
import textwrap
# We use typing for clearer function signatures.
from typing import Dict, List

# --- Third-party import ---
# We import the official Anthropic Python SDK to call Claude.
import anthropic


# This constant defines the exact PRD sections we want Claude to return (and that we will print).
PRD_SECTIONS: List[str] = [
    "Problem Statement",
    "Target Users",
    "User Stories (3)",
    "Success Metrics",
    "Technical Considerations",
    "Risks",
]


def slugify_feature_name(feature_idea: str) -> str:
    """
    Convert a free-text feature idea into a filesystem-safe name for the output file.
    """

    # Take the first line to avoid extremely long filenames.
    first_line = feature_idea.strip().splitlines()[0] if feature_idea.strip() else "feature"
    # Lowercase and replace non-alphanumeric characters with underscores.
    slug = re.sub(r"[^a-z0-9]+", "_", first_line.lower()).strip("_")
    # Fall back to a generic name if the idea doesn't produce a usable slug.
    return slug or "feature"


def build_system_prompt() -> str:
    """
    Create the detailed system instruction that defines the PM persona and output constraints.
    """

    # We keep the system prompt as a single string so it can be passed directly to Claude.
    return textwrap.dedent(
        """
        You are a senior Product Manager at a B2B SaaS company. You write clear, structured PRDs that engineering teams love.

        Output requirements:
        - Return a PRD with ONLY the following sections, in this exact order:
          1) Problem Statement
          2) Target Users
          3) User Stories (3)
          4) Success Metrics
          5) Technical Considerations
          6) Risks
        - Use the exact section header text shown above.
        - Keep the content concise, actionable, and implementation-oriented.
        - Under "User Stories (3)", include exactly 3 bullet points, each in the form: "As a <user>, I want <goal>, so that <benefit>."
        - Under "Success Metrics", include 3-5 bullet points with measurable metrics.
        - Under "Technical Considerations", include 3-6 bullet points (APIs, data, integrations, security, performance, rollout).
        - Under "Risks", include 3-6 bullet points with mitigation ideas.
        - Do NOT add any additional sections (no Summary, Goals, Non-Goals, Appendix, etc.).
        """
    ).strip()


def build_few_shot_messages() -> List[Dict[str, str]]:
    """
    Provide a few-shot example that demonstrates the EXACT PRD format we want Claude to follow.
    """

    # We include one example pair (user request -> assistant PRD) as a template.
    example_user = (
        "Feature idea: Add SSO (SAML) for enterprise customers so they can centrally manage access."
    )

    # The example assistant response includes the required sections and bullet formatting.
    example_assistant = textwrap.dedent(
        """
        Problem Statement
        Enterprise customers require centralized identity management and security controls. Without SAML SSO, admins must manage passwords manually, onboarding is slower, and security teams cannot enforce corporate authentication policies consistently.

        Target Users
        - IT Admins / Identity & Access Management (IAM) owners
        - Security teams (GRC / compliance)
        - Department admins provisioning users

        User Stories (3)
        - As an IT admin, I want to configure SAML SSO for my organization, so that employees can log in using our corporate identity provider.
        - As a security lead, I want to require SSO for all users in my org, so that authentication complies with our security policies.
        - As a department admin, I want new users to be automatically provisioned on first login, so that onboarding is fast and error-free.

        Success Metrics
        - % of enterprise orgs with SSO enabled within 30 days of GA
        - Reduction in password reset tickets from enterprise accounts
        - Login success rate for SSO flows (IdP initiated + SP initiated)
        - Time-to-onboard (invite -> first successful login) for enterprise users

        Technical Considerations
        - Support at least one IdP initially (Okta), then expand (Azure AD, Google Workspace)
        - Implement SAML metadata upload + ACS endpoint + certificate rotation handling
        - Store org-level SSO configuration securely and audit configuration changes
        - Add feature flag + staged rollout by workspace tier
        - Ensure fallback admin access and clear error logging for SSO failures

        Risks
        - Misconfiguration causes login lockouts; mitigate with a test connection flow + break-glass admin bypass.
        - Increased support load during setup; mitigate with guided UI, docs, and clear error messages.
        - Security regressions in auth; mitigate with threat modeling and security review before GA.
        """
    ).strip()

    # We return the few-shot messages in Claude "messages" format.
    return [
        {"role": "user", "content": example_user},
        {"role": "assistant", "content": example_assistant},
    ]


def parse_prd_sections(prd_text: str) -> Dict[str, str]:
    """
    Parse the model output into a dict of section -> content using the known section headers.
    """

    # Normalize newlines to keep parsing stable across platforms.
    text = prd_text.replace("\r\n", "\n").replace("\r", "\n").strip()

    # Build a regex that matches any of the exact headers on their own line.
    headers_pattern = "|".join(re.escape(h) for h in PRD_SECTIONS)
    splitter = re.compile(rf"^(?P<header>{headers_pattern})\s*$", re.MULTILINE)

    # Find all headers and their positions so we can slice sections out of the full text.
    matches = list(splitter.finditer(text))
    sections: Dict[str, str] = {}

    # If the model didn't follow the format, return the whole text under a fallback key.
    if not matches:
        return {"RAW_OUTPUT": text}

    # Slice content between successive headers.
    for i, match in enumerate(matches):
        header = match.group("header")
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        content = text[start:end].strip("\n").strip()
        sections[header] = content

    return sections


def format_prd_for_print(sections: Dict[str, str]) -> str:
    """
    Create a human-friendly, clearly separated PRD string for terminal and file output.
    """

    # If parsing failed, print the raw output so the user still gets something useful.
    if "RAW_OUTPUT" in sections:
        return sections["RAW_OUTPUT"] + "\n"

    # We use a consistent separator to make the terminal output easy to scan.
    separator = "\n" + ("-" * 60) + "\n"

    # We print sections in the required order, even if Claude omitted one (we'll show it as empty).
    blocks: List[str] = []
    for header in PRD_SECTIONS:
        content = sections.get(header, "").strip()
        blocks.append(f"{header}\n{content}".rstrip())

    return separator.join(blocks).strip() + "\n"


def main() -> None:
    """
    CLI entry point: reads input, calls Claude, prints PRD, and saves it to disk.
    """

    # Ask the user for the feature idea directly in the terminal.
    feature_idea = input("Enter a feature idea to generate a PRD for: ").strip()

    # Guard against empty input so we don't generate meaningless output files.
    if not feature_idea:
        print("No feature idea provided. Exiting.")
        return

    # Create an API client using the ANTHROPIC_API_KEY environment variable (preferred by Anthropic SDK).
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    # Build prompts: system persona + few-shot examples + the user's feature idea.
    system_prompt = build_system_prompt()
    few_shot = build_few_shot_messages()
    user_message = (
        "Feature idea: " + feature_idea + "\n\nReturn the PRD in the exact sectioned format."
    )

    # Call Claude to generate the PRD.
    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=900,
        system=system_prompt,
        messages=[
            *few_shot,
            {"role": "user", "content": user_message},
        ],
    )

    # Extract the text from the first content block of the response.
    prd_text = response.content[0].text

    # Parse the output into sections (so we can print with clean separators).
    sections = parse_prd_sections(prd_text)

    # Format the PRD for clear terminal display.
    formatted = format_prd_for_print(sections)

    # Print a visual header so the user can immediately see where the PRD begins.
    print("\n" + "=" * 60)
    print("GENERATED PRD")
    print("=" * 60 + "\n")

    # Print the PRD with section headers and separators.
    print(formatted)

    # Create the output folder if it doesn't exist.
    os.makedirs("output", exist_ok=True)

    # Generate a safe filename from the user's feature idea.
    feature_name = slugify_feature_name(feature_idea)

    # Build the output file path using the required naming scheme.
    output_path = os.path.join("output", f"{feature_name}.txt")

    # Save the PRD to disk so the user can reuse it later.
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(formatted)

    # Confirm where the PRD was saved.
    print(f"\nSaved PRD to: {output_path}")


# Run the CLI tool when the file is executed directly (and not when imported).
if __name__ == "__main__":
    main()

