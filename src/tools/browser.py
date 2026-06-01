"""
src/tools/browser.py
--------------------
High-level browser lifecycle management for the Web Automation Agent.

Why this module exists:
    Playwright's API is async and stateful — you must start a Playwright
    runtime, then launch a browser, then open a page, and later tear all
    three down in reverse order.  Wrapping these steps in named async
    functions keeps agent.py readable and ensures the teardown path is
    always the same regardless of how the session ends.

    All three functions operate on the shared `state` singleton so callers
    never have to pass browser handles around.

Usage:
    from src.tools.browser import open_browser, navigate_to_url, close_browser
"""

# `async_playwright` is the entry-point for Playwright's async API.
# It returns a context manager that starts the underlying browser server.
from playwright.async_api import async_playwright

# Shared mutable state that holds the live browser/page objects.
from src.tools.state import state

# Module-level logger singleton for consistent timestamped output.
from src.utils.logger import logger


async def open_browser() -> str:
    """
    Launch a visible Chromium browser at 1280×720 and store the handles
    in the shared `state` object.

    Why headless=False?
        Running the browser in visible (headed) mode lets developers watch
        the agent interact with the page in real time — invaluable for
        debugging mis-clicks or missed elements.

    Why 1280×720?
        The system prompt and coordinate logic all assume this exact
        viewport size.  Keeping the viewport constant means the AI's
        pixel-coordinate estimates remain accurate across different machines.

    Returns:
        A human-readable string confirming the result, which is also
        logged back into the AI conversation as a tool result.
    """
    # Guard against double-initialisation — Playwright will raise if you
    # try to launch a second browser while one is already running.
    if state.browser:
        return "Browser already open"

    logger.info("Launching Chromium (1280x720, visible)...")

    # Step 1: Start the Playwright runtime (manages the browser process).
    state.playwright = await async_playwright().start()

    # Step 2: Launch Chromium in headed mode so the session is visible.
    state.browser = await state.playwright.chromium.launch(headless=False)

    # Step 3: Open a new tab with a fixed viewport that matches the
    # coordinate space assumed by the vision model and the system prompt.
    state.page = await state.browser.new_page(viewport={"width": 1280, "height": 720})

    return "Browser launched successfully"


async def navigate_to_url(url: str) -> str:
    """
    Navigate the current browser tab to the given URL and wait until the
    network is idle (no pending requests for ≥500 ms).

    Waiting for `networkidle` is important because many modern web apps
    load critical content (forms, buttons) via async XHR/fetch calls
    *after* the initial HTML is rendered.  Without this wait, a screenshot
    taken immediately after navigation might not yet show those elements.

    Args:
        url: The fully-qualified URL to navigate to
             (e.g. "https://example.com/form").

    Returns:
        A confirmation string that is appended to the conversation as a
        tool result so the model knows navigation succeeded.
    """
    # Without an open page there is nothing to navigate — return an error
    # string instead of raising so the agent loop can handle it gracefully.
    if not state.page:
        return "Error: Browser not open"

    logger.info(f"Navigating to {url}")

    # `goto` triggers the navigation; `wait_for_load_state("networkidle")`
    # blocks until the page settles, reducing the chance of a screenshot
    # capturing a partially loaded UI.
    await state.page.goto(url)
    await state.page.wait_for_load_state("networkidle")

    return f"Navigated to {url}"


async def close_browser() -> str:
    """
    Tear down the browser and Playwright runtime in the correct order.

    Why order matters:
        Playwright's browser process is a child of the playwright runtime.
        Closing the browser first allows it to clean up open connections
        before the parent runtime is stopped.  Stopping the runtime first
        can leave zombie processes on some platforms.

    This function is idempotent — calling it when nothing is open is safe
    because each attribute is checked before the corresponding `.close()`
    or `.stop()` call.

    Returns:
        A confirmation string indicating the browser has been closed.
    """
    # Close the browser (and all its tabs) if one is currently open.
    if state.browser:
        await state.browser.close()
        # Nullify the reference so `if state.browser` checks return False
        # and the guard in open_browser() works correctly on re-entry.
        state.browser = None

    # Stop the Playwright runtime after the browser is fully closed.
    if state.playwright:
        await state.playwright.stop()
        state.playwright = None

    # Clear the page reference — it is now a dangling handle.
    state.page = None

    logger.info("Browser closed")
    return "Browser closed"
