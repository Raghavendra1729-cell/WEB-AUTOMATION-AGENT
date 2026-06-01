"""
src/agent/agent.py
------------------
Core agent loop for the Web Automation Agent.

Why this module exists:
    This is the "brain" of the project.  It ties every other module
    together into a single perception-decision-action loop:

      Perception  → take_screenshot()           (what does the page look like?)
      Decision    → Qwen2.5-VL via HuggingFace  (what should I do next?)
      Action      → execute_tool()              (do it in the real browser)

    The loop runs for at most 25 steps (a safety cap to prevent runaway
    API spend) and terminates early when the model signals "DONE".

    A try/finally block guarantees the browser is always closed, even if
    the model API raises an unhandled exception mid-session.

Architecture note:
    The model is accessed through the OpenAI-compatible SDK pointed at
    HuggingFace's inference router.  This means we can swap the underlying
    model by changing just the `model=` string in the API call.

Usage:
    from src.agent.agent import run_agent
    await run_agent(task="...", start_url="https://...")
"""

# `json` is used to parse the argument strings the model produces for
# tool calls — the API returns them as JSON-encoded strings, not dicts.
import json

# `AsyncOpenAI` is the async client for OpenAI-compatible APIs.
# We point it at HuggingFace's router endpoint instead of api.openai.com.
from openai import AsyncOpenAI

# The HuggingFace API token loaded from the .env file at startup.
from src.utils.config import HF_API_TOKEN

# Module-level logger singleton used throughout this file.
from src.utils.logger import logger

# The system prompt (model persona + rules) and the tool JSON schemas.
from src.agent.prompt import SYSTEM_PROMPT, TOOL_SCHEMAS

# Browser lifecycle helpers — open, navigate, and close the Chromium session.
from src.tools.browser import open_browser, navigate_to_url, close_browser

# Screenshot capture — returns a base64 JPEG for the multimodal message.
from src.tools.screenshot import take_screenshot

# Mouse interaction tools available to the model.
from src.tools.mouse import click_on_screen, double_click

# Keyboard tool — types text into the focused element.
from src.tools.keyboard import send_keys

# Page scrolling tool.
from src.tools.scroll import scroll


# ---------------------------------------------------------------------------
# API Client
# ---------------------------------------------------------------------------

# Build the AsyncOpenAI client once at module load time.
# `base_url` overrides the default OpenAI endpoint so that requests are
# routed to HuggingFace's OpenAI-compatible inference router instead.
# `api_key` carries the HuggingFace token for authentication.
client = AsyncOpenAI(
    base_url="https://router.huggingface.co/v1",
    api_key=HF_API_TOKEN
)


# ---------------------------------------------------------------------------
# Tool dispatcher map
# ---------------------------------------------------------------------------

# A plain dict that maps tool name strings (as used in the JSON schemas)
# to the actual async Python callables.  When the model returns a tool
# call, `execute_tool` looks up the function here by name and calls it
# with the parsed arguments.
#
# This pattern avoids a long if/elif chain and makes it trivial to add
# new tools: just import the function and add one line to this dict.
TOOLS: dict = {
    "click_on_screen": click_on_screen,
    "double_click": double_click,
    "send_keys": send_keys,
    "scroll": scroll,
}


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

async def execute_tool(name: str, arguments_str: str) -> str:
    """
    Parse a tool-call response from the model and execute the matching
    Python function.

    The model returns tool arguments as a JSON-encoded string (e.g.
    ``'{"x": 640, "y": 360}'``).  This function decodes that string,
    looks up the tool by name, and calls it with the decoded kwargs.

    Error handling strategy:
        All errors are caught and returned as descriptive strings rather
        than raising.  This way the error message is appended to the
        conversation as a tool result so the model can see what went wrong
        and potentially self-correct on the next step.

    Args:
        name:          The tool name exactly as it appears in TOOL_SCHEMAS
                       and the TOOLS dispatcher dict.
        arguments_str: A JSON-encoded string of keyword arguments, as
                       produced by the model (e.g. ``'{"x": 100, "y": 200}'``).

    Returns:
        The string result returned by the tool function, or an error
        string describing what went wrong.
    """
    # Step 1: Parse the JSON argument string into a Python dict.
    # The model occasionally produces malformed JSON (e.g. trailing commas),
    # so we wrap this in its own try/except to give a clear error message.
    try:
        args = json.loads(arguments_str)
    except Exception as e:
        return f"Error: Invalid arguments JSON: {e}"

    # Step 2: Look up the tool function by name.
    tool = TOOLS.get(name)
    if not tool:
        # Return an error — an unknown tool name usually means the model
        # hallucinated a tool that doesn't exist in the schema.
        return f"Error: Tool '{name}' not found in dispatcher"

    # Step 3: Call the tool with the parsed kwargs and return its result.
    try:
        result = await tool(**args)
        return result
    except Exception as e:
        # Catch any runtime error from the tool (e.g. Playwright timeout)
        # and surface it to the model as a tool result string.
        return f"Error executing tool '{name}': {e}"


# ---------------------------------------------------------------------------
# Main agent loop
# ---------------------------------------------------------------------------

async def run_agent(task: str, start_url: str) -> None:
    """
    Run the full perception–decision–action loop until the task is complete
    or the step limit is reached.

    Loop structure (per step):
        1. Take a screenshot of the current browser state.
        2. Append the screenshot as a multimodal user message.
        3. Call the vision-language model to decide the next action.
        4. If the model returns a tool call → execute it and append the result.
        5. If the model returns plain text containing "done" → stop the loop.

    Safety mechanisms:
        - **25-step cap**: Prevents infinite loops and unbounded API spend.
        - **try/finally**: Guarantees the browser is closed even if the model
          API or a tool raises an unhandled exception mid-session.
        - **API error catch**: A failed model call breaks the loop cleanly
          rather than crashing the process.

    Args:
        task:      A natural-language description of what the agent should
                   accomplish (e.g. "Fill in the Name field with 'Alice'
                   and submit the form.").
        start_url: The URL the browser should navigate to at the start of
                   the session before the agent loop begins.
    """
    logger.info("Starting Agent...")

    # Open the browser and navigate to the starting URL outside the
    # try block so that the logger sees these as the first logged actions.
    await open_browser()
    await navigate_to_url(start_url)

    # Seed the conversation with the system prompt and the initial task.
    # This list grows with every step as screenshots and tool results are
    # appended — it forms the "memory" the model sees at each decision point.
    messages: list[dict] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Task: {task}"},
    ]

    # ---------------------------------------------------------------------------
    # The try/finally guarantees close_browser() runs no matter what happens
    # inside the loop — including unhandled exceptions from the model API or
    # from any tool, and including a clean "DONE" exit or the step cap.
    # ---------------------------------------------------------------------------
    try:
        # Hard cap of 25 steps to prevent the agent from running forever
        # if it gets stuck in a loop or the "DONE" signal is never sent.
        for step in range(25):
            logger.info(f"--- Step {step + 1} ---")

            # --- Perception: Capture the current browser state ---
            # The screenshot is JPEG-compressed internally and returned as
            # a base64 string ready to embed in the multimodal message.
            screenshot_b64 = await take_screenshot()

            # --- Build the multimodal observation message ---
            # The OpenAI multimodal format requires `content` to be a list
            # of typed parts.  We include a text prompt alongside the image
            # so the model understands it should pick the next tool call.
            messages.append({
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "Here is the current browser screenshot. "
                            "What is the next tool to call to complete the task?"
                        ),
                    },
                    {
                        "type": "image_url",
                        # The `data:` URI scheme embeds the raw image bytes
                        # in the JSON payload, avoiding a separate file upload.
                        "image_url": {"url": f"data:image/jpeg;base64,{screenshot_b64}"},
                    },
                ],
            })

            # --- Decision: Ask the vision model what to do next ---
            try:
                response = await client.chat.completions.create(
                    # Qwen2.5-VL-72B is a state-of-the-art vision-language model.
                    # The `:cheapest` suffix routes to the lowest-cost provider
                    # on the HuggingFace router for this model.
                    model="Qwen/Qwen2.5-VL-72B-Instruct:cheapest",
                    messages=messages,
                    # Pass the tool schemas so the model knows which tools
                    # are available and how to call them.
                    tools=TOOL_SCHEMAS,
                    # `auto` lets the model decide whether to call a tool or
                    # respond with plain text (e.g. when signalling "DONE").
                    tool_choice="auto",
                )
            except Exception as e:
                logger.error(f"API Error calling model: {e}")
                # Exit the loop — we can't continue without model decisions.
                break

            # Extract the first (and usually only) response choice.
            choice = response.choices[0].message

            # --- Append the assistant message to conversation history ---
            # BUG FIX: The OpenAI SDK returns `choice` as a Pydantic model
            # object (ChatCompletionMessage), not a plain dict.  The messages
            # list must contain dicts for the API to accept them on the next
            # call.  We serialise the assistant turn manually here.
            #
            # When the model makes a tool call, `choice.tool_calls` is a list
            # of ChoiceDeltaToolCall objects.  We convert each one to the dict
            # format the API expects: {"id", "type", "function": {"name", "arguments"}}.
            assistant_message: dict = {
                "role": "assistant",
                # `choice.content` may be None when the model only returns a
                # tool call and no accompanying text — the API accepts None here.
                "content": choice.content,
            }

            if choice.tool_calls:
                # Serialise each tool call into a plain dict so the messages
                # list remains JSON-serialisable for the next API request.
                assistant_message["tool_calls"] = [
                    {
                        "id": tc.id,           # Unique ID linking this call to its result
                        "type": tc.type,       # Always "function" in the current API version
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,  # JSON string
                        },
                    }
                    for tc in choice.tool_calls
                ]

            # Now it is safe to append — `assistant_message` is a plain dict.
            messages.append(assistant_message)

            # --- Action: Execute the tool (or check for completion) ---
            if choice.tool_calls:
                # Take only the first tool call per step.  Some models may
                # return multiple calls, but for visual automation one action
                # at a time is safer — we need a fresh screenshot after each.
                tool_call = choice.tool_calls[0]
                name = tool_call.function.name
                args = tool_call.function.arguments

                logger.info(f"AI suggests tool: {name}({args})")

                # Execute the tool and capture the string result.
                result = await execute_tool(name, args)
                logger.info(f"Tool execution result: {result}")

                # Append the tool result to the conversation so the model
                # can see the outcome of its action at the next step.
                # `tool_call_id` must match the `id` from the assistant
                # message above — the API uses this to pair calls with results.
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": name,
                    "content": result,
                })

            else:
                # The model responded with plain text (no tool call).
                # This is how it signals that the task is complete.
                content: str = choice.content or ""
                logger.info(f"AI response: {content}")

                # Check for the "DONE" keyword defined in the system prompt.
                # We use `.lower()` to handle "Done", "done", "DONE", etc.
                if "done" in content.lower():
                    logger.info("Task completed — agent signalled DONE.")
                    break

    finally:
        # This block runs whether the loop exited normally (DONE / step cap)
        # or crashed with an exception.  It ensures the Chromium process is
        # always terminated cleanly, preventing zombie browser windows.
        await close_browser()
        logger.info("Finished.")
