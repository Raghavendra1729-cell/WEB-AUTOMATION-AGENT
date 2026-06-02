"""
Core agent loop for the Web Automation Agent.
"""

import json
import re
from openai import AsyncOpenAI

from src.agent.prompt import SYSTEM_PROMPT
from src.tools.browser import close_browser, navigate_to_url, open_browser
from src.tools.keyboard import send_keys, press_key
from src.tools.mouse import click_on_screen, double_click
from src.tools.screenshot import take_screenshot
from src.tools.scroll import scroll
from src.tools.state import state
from src.tools.wait import wait
from src.utils.config import HF_API_TOKEN
from src.utils.logger import logger

client = AsyncOpenAI(
    base_url="https://router.huggingface.co/v1",
    api_key=HF_API_TOKEN
)

TOOLS: dict = {
    "click_on_screen": click_on_screen,
    "double_click": double_click,
    "send_keys": send_keys,
    "press_key": press_key,
    "scroll": scroll,
    "wait": wait,
}

MAX_REPEAT_COUNT = 3


async def execute_tool(name: str, args: dict) -> str:
    """Look up a tool by name and call it with the given args dict."""
    tool = TOOLS.get(name)
    if not tool:
        return f"Error: Tool '{name}' not found"

    try:
        result = await tool(**args)
        return result
    except Exception as e:
        return f"Error executing tool '{name}': {e}"


def extract_json(content: str) -> dict:
    """Extract a JSON object from the model's text response."""
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", content, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse JSON from markdown: {e}")

    match = re.search(r"\{.*\}", content, re.DOTALL)
    if match:
        raw = match.group(0)
        raw = re.sub(r':\s*(\d+)\]', r': \1}', raw)
        try:
            return json.loads(raw)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse JSON from raw text: {e}")

    raise ValueError(f"No JSON object found in: {content}")


def sanitize_args(args: dict) -> dict:
    """Fix common model output quirks."""
    cleaned = {}
    for k, v in args.items():
        if isinstance(v, list) and len(v) == 1:
            v = v[0]
        if k in ("x", "y", "amount") and isinstance(v, str):
            try:
                v = int(v)
            except ValueError:
                pass
        cleaned[k] = v
    return cleaned


def make_action_key(name: str, args: dict) -> str:
    """Create a hashable string from an action for repeat detection."""
    try:
        return f"{name}:{json.dumps(args, sort_keys=True)}"
    except (TypeError, ValueError) as e:
        return f"{name}:{str(args)}"


def strip_old_images(messages: list[dict]) -> None:
    """Remove image_url parts from ALL previous user messages in-place."""
    for msg in messages:
        if msg.get("role") == "user" and isinstance(msg.get("content"), list):
            msg["content"] = [
                p for p in msg["content"]
                if not (isinstance(p, dict) and p.get("type") == "image_url")
            ]


async def run_agent(task: str, start_url: str) -> None:
    """Perception-decision-action loop."""
    logger.info("Starting Agent...")
    
    try:
        await open_browser()
        nav_result = await navigate_to_url(start_url)
        if nav_result.startswith("Error") and (not state.page or state.page.is_closed()):
            logger.error("Browser closed during initial navigation. Aborting.")
            return

        messages: list[dict] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Task: {task}"},
        ]

        last_action_key: str = ""
        repeat_count: int = 0

        for step in range(25):
            logger.info(f"--- Step {step + 1} ---")

            if not state.page or state.page.is_closed():
                logger.error("Browser page is closed — stopping agent.")
                break

            strip_old_images(messages)

            try:
                screenshot_b64 = await take_screenshot()
            except Exception as e:
                logger.error(f"Screenshot failed (browser likely closed): {e}")
                break

            messages.append({
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "Here is the current browser screenshot. "
                            "What is the next tool to call to complete the task? "
                            "Respond with a JSON object containing 'reasoning', 'tool', and 'args'."
                        ),
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{screenshot_b64}"},
                    },
                ],
            })

            response = None
            import asyncio
            for retry in range(3):
                try:
                    response = await client.chat.completions.create(
                        model="Qwen/Qwen2.5-VL-72B-Instruct:cheapest",
                        messages=messages,
                    )
                    break
                except Exception as e:
                    logger.error(f"API Error calling model (attempt {retry+1}): {e}")
                    if retry == 2:
                        break
                    await asyncio.sleep(2)
            
            if not response:
                logger.error("Failed to get API response after 3 retries. Stopping.")
                break

            choice = response.choices[0].message
            content: str = choice.content or ""
            logger.info(f"AI raw response: {content}")
            messages.append({"role": "assistant", "content": content})

            try:
                action = extract_json(content)
                name = action.get("tool", "").lower().strip()
                args = sanitize_args(action.get("args", {}))

                if name == "done":
                    logger.info("✅ Task completed — agent signalled DONE.")
                    break

                action_key = make_action_key(name, args)
                if action_key == last_action_key:
                    repeat_count += 1
                else:
                    repeat_count = 1
                    last_action_key = action_key

                if repeat_count >= MAX_REPEAT_COUNT:
                    logger.info(
                        f"⚠️  Same action repeated {repeat_count}x — "
                        f"nudging AI to try something different."
                    )
                    messages.append({
                        "role": "user",
                        "content": (
                            f"WARNING: You have repeated the exact same action "
                            f"'{name}({args})' {repeat_count} times with no change. "
                            f"The page looks identical. Either the task is already "
                            f"done (call done tool), or you need a completely "
                            f"different approach. Look at the screenshot carefully."
                        ),
                    })
                    if repeat_count >= MAX_REPEAT_COUNT + 2:
                        logger.info("🛑 Agent stuck — forcing stop after too many repeats.")
                        break
                    continue

                logger.info(f"AI suggests tool: {name}({args})")
                result = await execute_tool(name, args)
                logger.info(f"Tool execution result: {result}")

                if "Target page, context or browser has been closed" in result:
                    logger.error("Browser died during tool execution — stopping.")
                    break

                messages.append({
                    "role": "user",
                    "content": f"Tool '{name}' returned: {result}",
                })

            except Exception as e:
                logger.error(f"Failed to parse or execute action: {e}")
                messages.append({
                    "role": "user",
                    "content": (
                        f"Error: {e}\n"
                        f"Please respond with a valid JSON object like: "
                        f'{{"reasoning": "I need to click...", "tool": "click_on_screen", "args": {{"x": 320, "y": 180}}}}'
                    ),
                })

    finally:
        try:
            await close_browser()
        except Exception as e:
            logger.error(f"Error while closing browser: {e}")
        logger.info("Finished.")
