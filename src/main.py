"""
src/main.py
-----------
Entry point for the Web Automation Agent.

Why this module exists:
    `main.py` is the single place where:
      - The target URL is defined.
      - The task description is written in plain English.
      - The asyncio event loop is started.

    Keeping configuration here (rather than inside agent.py) means you can
    point the agent at a different page or give it a new task by editing
    just this file — without touching any agent logic.

Running the agent:
    python -m src.main
    # or, from the project root:
    python src/main.py
"""

# `asyncio` is Python's standard library for running async code.
# Since Playwright and the OpenAI client are both async, the entire agent
# is an async function that must be driven by an event loop.
import asyncio

# The top-level agent coroutine that orchestrates the full session.
from src.agent.agent import run_agent


# ---------------------------------------------------------------------------
# Task definition
# ---------------------------------------------------------------------------

# A multi-step natural-language instruction set for the vision model.
# The numbered steps help the model follow a logical sequence, but the model
# is free to deviate if the page layout requires it.
TASK: str = """
1. Find the form on the page (it has Name and Description fields)
2. Scroll down if needed to find it
3. Click on the Name field and type "Lingam Raghavendra"
4. Click on the Description field and type "Automated by Web Automation Agent"
5. Click the Submit button
6. Take a final screenshot to confirm, then say DONE
"""

# The starting URL the browser will navigate to before the agent loop begins.
# This is the shadcn/ui docs page that contains the react-hook-form example
# with the Name + Description form we want to automate.
START_URL: str = "https://ui.shadcn.com/docs/forms/react-hook-form"


# ---------------------------------------------------------------------------
# Async entry point
# ---------------------------------------------------------------------------

async def main() -> None:
    """
    Async wrapper that kicks off the agent session.

    Why async?
        `run_agent` is an async function because it uses Playwright (async)
        and the OpenAI SDK (async).  All I/O-bound work happens concurrently
        inside the event loop, so the process never blocks a thread while
        waiting for network responses or browser events.

    This wrapper exists so we can call `asyncio.run(main())` at the bottom,
    which creates a fresh event loop, runs `main` to completion, and then
    closes the loop cleanly.
    """
    # Delegate all work to the agent — this function is intentionally thin.
    await run_agent(TASK, START_URL)


# ---------------------------------------------------------------------------
# Script entry guard
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # `asyncio.run` is the idiomatic way to start an async program in
    # Python 3.7+.  It creates the event loop, runs the coroutine to
    # completion, and then closes the loop (which also cancels any lingering
    # tasks and closes file descriptors).
    asyncio.run(main())
