"""
src/tools/state.py
------------------
Shared mutable state container for the browser session.

Why this module exists:
    Playwright's browser, page, and playwright-runtime objects must be
    accessible across many independent tool modules (browser.py, mouse.py,
    screenshot.py, etc.) without passing them as function arguments through
    every call site.

    A module-level singleton — `state` — acts as a lightweight dependency
    injection container.  All tool modules import this single object and
    read/write its attributes.  Because Python module imports are cached,
    every importer receives the **same** BrowserState instance, making
    shared state safe without any extra synchronisation.

Usage:
    from src.tools.state import state
    state.page.goto(url)      # read
    state.step_count += 1     # write
"""


class BrowserState:
    """
    A plain data container that holds the live Playwright objects for
    the current browser session.

    Attributes:
        playwright: The AsyncPlaywright instance that manages the
            underlying browser process.  Must be started before any
            browser can be launched and must be stopped on teardown.
        browser: The Chromium Browser instance.  Created by open_browser()
            and torn down by close_browser().
        page: The active browser tab/page.  All interaction tools
            (click, scroll, keyboard, screenshot) operate on this object.
        step_count: An incrementing counter used by the screenshot tool
            to give each screenshot a sequential filename
            (step_001.png, step_002.png, …).  Keeping it here avoids a
            global variable in screenshot.py.

    Design note:
        Attributes are intentionally initialised to `None` / `0` so that
        any module can safely check `if state.page:` before attempting an
        operation, enabling graceful "browser not open" error messages.
    """

    def __init__(self) -> None:
        # Playwright runtime handle — needed to call `.stop()` cleanly on exit.
        self.playwright = None

        # The Chromium browser process handle.
        self.browser = None

        # The current browser tab.  All automation actions target this object.
        self.page = None

        # Counter that increments with every screenshot so files are named
        # step_001.png, step_002.png, … in chronological order.
        self.step_count: int = 0


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

# One shared instance for the entire process lifetime.
# All tool modules import this object directly:
#   from src.tools.state import state
state = BrowserState()
