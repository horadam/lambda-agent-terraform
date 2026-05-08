import logging
import os
from datetime import datetime
import anthropic

logger = logging.getLogger(__name__)

MODEL = "claude-sonnet-4-6"

# Lazy singleton — created on first call so secrets.py has already run by then.
_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    return _client

TOOLS = [
    {
        "name": "get_current_time",
        "description": "Returns the current date and time.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    }
]


def get_current_time() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def run_agent(user_input: str) -> str:
    messages = [{"role": "user", "content": user_input}]

    while True:
        response = _get_client().messages.create(
            model=MODEL,
            max_tokens=1024,
            tools=TOOLS,
            messages=messages,
        )

        if response.stop_reason == "end_turn":
            for block in response.content:
                if hasattr(block, "text"):
                    return block.text
            return ""

        if response.stop_reason == "tool_use":
            tool_use_block = next(b for b in response.content if b.type == "tool_use")
            logger.info("tool call: %s", tool_use_block.name)
            tool_result = get_current_time()
            logger.info("tool result: %s", tool_result)

            messages.append({"role": "assistant", "content": response.content})
            messages.append({
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": tool_use_block.id,
                        "content": tool_result,
                    }
                ],
            })
        else:
            # Unexpected stop reason — return whatever text we have
            for block in response.content:
                if hasattr(block, "text"):
                    return block.text
            return ""
