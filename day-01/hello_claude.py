"""Simple script that sends a message to Claude using the Anthropics Python SDK."""

# This line imports the standard library module that lets us read environment variables from the operating system.
import os

# This line imports the official Anthropic Python client library so we can talk to Claude.
import anthropic

# This line reads your Anthropic API key from the ANTHROPIC_API_KEY environment variable.
api_key = os.environ["ANTHROPIC_API_KEY"]

# This line creates a Claude client instance that will use your API key to authenticate requests.
client = anthropic.Anthropic(api_key=api_key)

# This line calls Claude's Messages API with a system prompt and a single user message and waits for the response.
response = client.messages.create(
    system="You are a helpful AI PM assistant.",
    model="claude-sonnet-4-6",
    max_tokens=300,
    messages=[
        {
            "role": "user",
            "content": "Tell me in 3 bullet points why AI agents are important for enterprise automation",
        }
    ],
)
reply_text = response.content[0].text
print(reply_text)

