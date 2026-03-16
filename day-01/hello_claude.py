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
    # This line tells Claude how it should behave during the conversation.
    system="You are a helpful AI PM assistant.",
    # This line selects which Claude model to use for generating the response.
    model="claude-sonnet-4-6",
    # This line sets the maximum number of output tokens Claude is allowed to generate.
    max_tokens=300,
    # This line provides the conversation messages, starting with what the user says.
    messages=[
        {
            # This line marks the role of the message as the human user speaking to Claude.
            "role": "user",
            # This line contains the actual question we want Claude to answer in 3 bullet points.
            "content": "Tell me in 3 bullet points why AI agents are important for enterprise automation",
        }
    ],
)

# This line pulls out the text content from the first part of Claude's reply.
reply_text = response.content[0].text

# This line prints Claude's reply to your terminal so you can read the 3 bullet points.
print(reply_text)

