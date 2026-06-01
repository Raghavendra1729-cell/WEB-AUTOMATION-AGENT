"""
src/utils/logger.py
-------------------
Lightweight, opinionated logger for the Web Automation Agent.

Why this module exists:
    Python's built-in `logging` module is powerful but verbose to configure.
    For a single-process automation script we only need two levels —
    informational progress updates and errors — so a tiny wrapper around
    `print` is clearer and has no configuration overhead.

    The module exposes a **singleton** `logger` instance so every part
    of the codebase imports the same object and shares the same output
    stream without any wiring code.

Usage:
    from src.utils.logger import logger
    logger.info("Step complete")
    logger.error("Something went wrong")
"""

# `sys` is needed to write error messages to stderr (separate from stdout
# so that log collectors can filter errors independently).
import sys

# `datetime` provides human-readable timestamps without pulling in a heavy
# third-party library.
from datetime import datetime


class Logger:
    """
    A minimal two-level logger that writes timestamped, emoji-prefixed
    messages to stdout (info) and stderr (error).

    Design decisions:
    - Timestamps use HH:MM:SS only — date is omitted because automation
      runs are short-lived and the date adds visual noise.
    - Emoji icons (🟢 / 🔴) give an instant visual cue when tailing logs
      in a terminal without needing colour ANSI codes.
    - `flush=True` forces output to appear immediately, which is important
      when the process output is piped or captured by another tool.
    """

    def info(self, msg: str) -> None:
        """
        Log an informational message to stdout.

        Args:
            msg: The human-readable message describing the current action
                 or state of the agent (e.g. "Navigating to https://...").
        """
        # Build a concise timestamp prefix so developers can time each step.
        time_str = datetime.now().strftime("%H:%M:%S")

        # Print to stdout — the default file for `print`.
        # `flush=True` ensures the line is written even if the process is
        # running inside a buffered pipe or a CI log collector.
        print(f"[{time_str}] 🟢 {msg}", flush=True)

    def error(self, msg: str) -> None:
        """
        Log an error message to stderr.

        Writing errors to stderr (rather than stdout) keeps them separate
        from normal progress output, which is useful when redirecting or
        piping agent output in shell scripts.

        Args:
            msg: A description of what went wrong, ideally including
                 enough context to identify the failing operation.
        """
        time_str = datetime.now().strftime("%H:%M:%S")

        # `file=sys.stderr` routes this message to the error stream so it
        # can be captured independently of normal stdout log lines.
        print(f"[{time_str}] 🔴 ERROR: {msg}", file=sys.stderr, flush=True)


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

# Instantiate once at import time so callers never have to manage lifecycle.
# All modules do `from src.utils.logger import logger` and use it directly.
logger = Logger()
