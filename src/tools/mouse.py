"""
src/tools/mouse.py
------------------
Mouse interaction tools for the Web Automation Agent.

Why this module exists:
    Playwright exposes mouse operations through `page.mouse`, a low-level
    object that requires knowing pixel coordinates.  This module wraps
    those calls with guard checks, logging, and human-readable return
    values so they can be safely dispatched from the agent's tool loop.

    Both functions follow the same pattern:
      1. Verify the browser is open.
      2. Log the action so developers can trace the agent's decisions.
      3. Execute the Playwright mouse call.
      4. Return a confirmation string for the AI's conversation history.

Usage:
    from src.tools.mouse import click_on_screen, double_click
"""

# Shared browser session — `state.page` is the target of all mouse actions.
from src.tools.state import state

# Consistent timestamped logging across all tool modules.
from src.utils.logger import logger


async def click_on_screen(x: int, y: int) -> str:
    """
    Perform a single left-click at the given viewport coordinates.

    The AI agent uses visual estimation on the 1280×720 screenshot to
    decide where to click.  This function translates that coordinate
    decision into a real Playwright mouse event on the live browser.

    Args:
        x: Horizontal pixel position (0 = left edge, 1280 = right edge).
        y: Vertical pixel position (0 = top edge, 720 = bottom edge).

    Returns:
        A confirmation string describing the action taken, which is
        appended to the conversation as a tool result so the AI knows
        the click was executed.
    """
    # Without an open page, Playwright has nowhere to send the click event.
    # Returning an error string (rather than raising) lets the agent loop
    # log the failure and decide whether to continue or abort.
    if not state.page:
        return "Error: Browser not open"

    logger.info(f"Clicking at ({x}, {y})")

    # `page.mouse.click` dispatches a full click sequence:
    # mousedown → mouseup → click, mimicking a real user interaction.
    await state.page.mouse.click(x, y)

    return f"Clicked at ({x}, {y})"


async def double_click(x: int, y: int) -> str:
    """
    Perform a double-click at the given viewport coordinates.

    Double-clicking is required for actions like selecting a word in a
    text field or activating elements that only respond to dblclick events.

    Args:
        x: Horizontal pixel position (0–1280).
        y: Vertical pixel position (0–720).

    Returns:
        A confirmation string describing the action, appended to the
        conversation as a tool result.
    """
    if not state.page:
        return "Error: Browser not open"

    logger.info(f"Double clicking at ({x}, {y})")

    # `dblclick` fires: mousedown → mouseup → click → mousedown → mouseup
    # → click → dblclick — the full sequence a real browser expects.
    await state.page.mouse.dblclick(x, y)

    return f"Double clicked at ({x}, {y})"
