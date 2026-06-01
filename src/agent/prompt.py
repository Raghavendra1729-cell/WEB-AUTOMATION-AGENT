"""
src/agent/prompt.py
-------------------
System prompt and tool schema definitions for the Web Automation Agent.

Why this module exists:
    The vision-language model (Qwen2.5-VL) needs two pieces of information
    to operate correctly:

      1. **SYSTEM_PROMPT** — A natural-language instruction set that tells
         the model *what role it plays*, *what rules to follow*, and *how
         to signal task completion*.  By keeping this in its own module,
         prompt engineering changes never require touching agent.py logic.

      2. **TOOL_SCHEMAS** — A list of JSON Schema objects in the OpenAI
         function-calling format that tells the model *which tools are
         available* and *what parameters each tool accepts*.  The API uses
         these schemas to constrain and parse the model's tool-call
         responses, so they must exactly match the Python function
         signatures in the tools/ package.

Usage:
    from src.agent.prompt import SYSTEM_PROMPT, TOOL_SCHEMAS
"""

# ---------------------------------------------------------------------------
# System Prompt
# ---------------------------------------------------------------------------

# The system prompt is the first message in every conversation and remains
# constant across all steps.  It establishes the model's persona, the
# coordinate system, and the stopping condition.
SYSTEM_PROMPT: str = """You are a browser automation agent. You control a real Chromium browser.
The viewport is exactly 1280x720. 

For every step, you will be given the current screenshot of the browser window.
Identify the location of elements using visual estimation of pixel coordinates on this 1280x720 canvas.
Choose the correct action to proceed with the user's task.

Rules:
1. Coordinates are from (0,0) (top-left) to (1280, 720) (bottom-right).
2. If you need to click an element, estimate its center point and call click_on_screen(x, y).
3. If you need to type, click the target field first to focus it, then call send_keys(text).
4. If the form or target is not visible, use scroll(direction='down', amount=500) to find it.
5. When the task is complete, respond with "DONE" in your thoughts/response. Do not call any more tools.
"""

# ---------------------------------------------------------------------------
# Tool Schemas (OpenAI function-calling format)
# ---------------------------------------------------------------------------

# Each entry in this list is an OpenAI-compatible tool specification.
# The `type: "function"` wrapper and the nested `function` object are
# required by the API.  The `parameters` follow JSON Schema conventions.
#
# IMPORTANT: The `name` field in each schema MUST exactly match the
# key used in the `TOOLS` dispatcher dict in agent.py and the actual
# Python function name in the tools/ package — the API uses the name
# to route the model's tool-call response to the right executor.
TOOL_SCHEMAS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "click_on_screen",
            "description": "Click at coordinates (x, y) on the viewport.",
            "parameters": {
                "type": "object",
                "properties": {
                    # Both x and y are integers because Playwright's mouse API
                    # works with whole pixel values; floats would be truncated anyway.
                    "x": {"type": "integer", "description": "X coordinate (0-1280)"},
                    "y": {"type": "integer", "description": "Y coordinate (0-720)"}
                },
                # `required` tells the model it must supply both coordinates —
                # a click without a position is meaningless.
                "required": ["x", "y"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "double_click",
            "description": "Double click at coordinates (x, y) on the viewport.",
            "parameters": {
                "type": "object",
                "properties": {
                    "x": {"type": "integer", "description": "X coordinate (0-1280)"},
                    "y": {"type": "integer", "description": "Y coordinate (0-720)"}
                },
                "required": ["x", "y"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "send_keys",
            "description": "Type text into the currently focused input element.",
            "parameters": {
                "type": "object",
                "properties": {
                    # A single `text` parameter — the model must decide what
                    # to type before calling this tool.
                    "text": {"type": "string", "description": "The text to type"}
                },
                "required": ["text"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "scroll",
            "description": "Scroll the page up or down.",
            "parameters": {
                "type": "object",
                "properties": {
                    # `enum` restricts the model to only the two valid directions,
                    # preventing typos like "downward" or "DOWN".
                    "direction": {
                        "type": "string",
                        "enum": ["up", "down"],
                        "description": "Direction to scroll"
                    },
                    "amount": {
                        "type": "integer",
                        "description": "Amount in pixels to scroll"
                    }
                },
                "required": ["direction", "amount"]
            }
        }
    }
]
