"""
src/tools/scroll.py
-------------------
Page scrolling tool for the Web Automation Agent.

Why this module exists:
    Many web pages render content below the visible viewport, including
    forms, buttons, and other interactive elements the agent needs to
    reach.  This module provides a simple interface for scrolling the
    page up or down by a configurable number of pixels.

    Playwright's `mouse.wheel` dispatches a native scroll event — more
    reliable than JavaScript `window.scrollBy` for pages with custom
    scroll containers or sticky headers that intercept JS scroll calls.

Usage:
    from src.tools.scroll import scroll
"""

# Shared browser session — `state.page.mouse` is used to fire the scroll.
from src.tools.state import state

# Consistent timestamped logging across all tool modules.
from src.utils.logger import logger


async def scroll(direction: str, amount: int) -> str:
    """
    Scroll the active browser page up or down by a given number of pixels.

    Playwright's `mouse.wheel(deltaX, deltaY)` simulates the mouse wheel.
    A positive `deltaY` scrolls **down** (content moves up), and a
    negative `deltaY` scrolls **up** (content moves down), matching the
    convention used by all major operating systems.

    After scrolling, the function waits 500 ms to allow scroll animations
    and any lazy-loaded content to finish rendering before the agent takes
    the next screenshot.

    Args:
        direction: Either ``"down"`` (to reveal content below the fold)
                   or ``"up"`` (to return to content above).
                   Case-insensitive.
        amount:    Number of pixels to scroll.  A value of 300–500 is
                   typically enough to reveal one screen-height of new
                   content; larger values jump further in one step.

    Returns:
        A string describing the scroll action that was performed, or an
        error string if the direction is unrecognised or the browser is
        not open.
    """
    # Without an open page there is no scroll target — return an error
    # string so the agent loop can handle the failure gracefully.
    if not state.page:
        return "Error: Browser not open"

    logger.info(f"Scrolling {direction} by {amount}px")

    if direction.lower() == "down":
        # Positive deltaY moves the viewport downward — revealing content
        # further down the page (below the current visible area).
        await state.page.mouse.wheel(0, amount)

    elif direction.lower() == "up":
        # Negative deltaY moves the viewport upward — returning to content
        # that has scrolled above the current visible area.
        await state.page.mouse.wheel(0, -amount)

    else:
        # Return an error rather than silently doing nothing so the model
        # receives feedback and can self-correct on the next step.
        return f"Error: Unknown scroll direction '{direction}'. Use 'up' or 'down'."

    # Wait for scroll animations and lazy-loaded content to settle before
    # the next screenshot is taken.  500 ms is enough for most CSS
    # transitions and IntersectionObserver callbacks.
    await state.page.wait_for_timeout(500)

    return f"Scrolled {direction} by {amount}px"
