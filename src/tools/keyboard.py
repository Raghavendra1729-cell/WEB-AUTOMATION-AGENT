"""
src/tools/keyboard.py
---------------------
Keyboard input tool for the Web Automation Agent.

Why this module exists:
    Typing text into a browser element via Playwright requires the element
    to already have keyboard focus.  The agent is responsible for clicking
    the target field first (using mouse.py) and then calling this module's
    `send_keys` function to type the desired text.

    Keeping keyboard logic in its own module maintains the single-
    responsibility principle — each file handles one category of browser
    interaction — and makes it easy to extend later (e.g. adding
    `press_key` for special keys like Tab or Enter).

Usage:
    from src.tools.keyboard import send_keys
"""

# Shared browser session — `state.page.keyboard` is the Playwright object
# that dispatches key events to whatever element currently has focus.
from src.tools.state import state

# Consistent timestamped logging across all tool modules.
from src.utils.logger import logger


async def send_keys(text: str) -> str:
    """
    Type a string of text into the currently focused browser element.

    Playwright's `keyboard.type` method dispatches individual `keydown`,
    `keypress`, and `keyup` events for each character, closely mimicking
    a real user typing.  This triggers JavaScript `oninput` and `onchange`
    handlers that some frameworks rely on for live validation.

    Important:
        The caller must ensure the target input field is focused **before**
        calling this function — typically by calling `click_on_screen` on
        the field first.  Typing without focus will send keystrokes to
        whatever element last received a click, or to no element at all.

    Args:
        text: The string to type into the focused element.
              Special characters are typed as-is; use `page.keyboard.press`
              for named keys (Tab, Enter, etc.) if that is needed in future.

    Returns:
        A confirmation string describing what was typed, appended to the
        AI conversation as a tool result.
    """
    # Guard against typing into a non-existent page — return a clear
    # error so the agent can decide whether to retry or abort.
    if not state.page:
        return "Error: Browser not open"

    logger.info(f"Typing: {text}")

    # `keyboard.type` simulates real character-by-character typing,
    # which is more compatible with JavaScript event listeners than
    # directly setting an element's `.value` property via JS injection.
    await state.page.keyboard.type(text)

    return f"Typed: {text}"
