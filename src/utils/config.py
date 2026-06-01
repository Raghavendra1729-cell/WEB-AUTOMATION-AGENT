"""
src/utils/config.py
-------------------
Centralised configuration loader for the Web Automation Agent.

Why this module exists:
    Rather than scattering `os.getenv()` calls throughout the codebase,
    every secret / setting is loaded once here and imported by name
    wherever it is needed. This makes secrets easy to audit and swap.

Usage:
    from src.utils.config import HF_API_TOKEN
"""

# Standard-library module for reading environment variables.
import os

# `python-dotenv` reads a `.env` file in the project root and injects its
# key=value pairs into os.environ **before** our getenv calls below.
# This lets developers keep secrets out of version control while still
# having them available at runtime.
from dotenv import load_dotenv

# Load .env into the process environment as early as possible so that
# subsequent `os.getenv` calls always see the values from that file.
load_dotenv()

# ------------------------------------------------------------------
# API Tokens
# ------------------------------------------------------------------

# HuggingFace Inference Router token.
# Used by agent.py when constructing the AsyncOpenAI client that points
# at `https://router.huggingface.co/v1`.
HF_API_TOKEN: str | None = os.getenv("HF_API_TOKEN")

# Warn loudly at startup if the token is missing — the agent will fail
# with an authentication error the moment it calls the model, so surfacing
# the problem here saves debugging time later.
if not HF_API_TOKEN:
    print(
        "[Warning] HF_API_TOKEN not found in environment or .env file. "
        "The agent will fail when it tries to call the HuggingFace API."
    )
