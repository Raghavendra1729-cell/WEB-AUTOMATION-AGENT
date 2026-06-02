"""
Entry point for the Web Automation Agent.
"""

import asyncio
from src.agent.agent import run_agent
from src.utils.logger import logger

TASK = """
1. You are on the Wikipedia homepage.
2. Click the main search input field and type "Artificial Intelligence".
3. Click the Search button (or the magnifying glass icon) to submit the search.
4. Once the new page loads, scroll down once to view the introduction.
5. Take a final look, then say DONE.
"""

START_URL = "https://www.wikipedia.org/"

async def main():
    try:
        await run_agent(TASK, START_URL)
    except Exception as e:
        logger.error(f"Agent crashed: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Agent stopped by user.")
    except Exception as e:
        print(f"Fatal error: {e}")
