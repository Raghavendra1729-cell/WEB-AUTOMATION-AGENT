# Web Automation Agent - Architecture Documentation

This document provides a complete technical explanation of how the Web Automation Agent operates. All inline conversational code comments have been removed to keep the codebase clean, as per best practices. This document serves as the official reference for the system's inner workings.

## System Overview
The Web Automation Agent uses a Large Vision-Language Model (VLM), specifically `Qwen2.5-VL-72B-Instruct` via the HuggingFace Inference API, to autonomously drive a Chromium browser using Playwright. 

The architecture is split into three main layers:
1. **The Tools (`src/tools/`)**: Wrappers around Playwright that expose atomic browser actions.
2. **The Agent Loop (`src/agent/`)**: The core logic that orchestrates screenshots, communicates with the VLM, and executes tools.
3. **The State (`src/tools/state.py`)**: A centralized singleton that tracks the live Playwright browser instance.

---

## 1. State Management (`src/tools/state.py`)
Because Playwright operates asynchronously and requires persistent connection handles to the browser and page, we maintain a global `BrowserState` singleton.
- `state.playwright`: The core Playwright runtime process.
- `state.browser`: The Chromium browser instance.
- `state.page`: The current active tab.
- `state.step_count`: Tracks the number of actions taken, used primarily for screenshot numbering.

By using a singleton, our tool functions do not need to constantly pass `page` objects back and forth.

---

## 2. Browser Tooling (`src/tools/`)

### Browser Lifecycle (`browser.py`)
- **`open_browser()`**: Initializes Playwright and launches Chromium. We force a strict `1280x720` viewport. Keeping a constant viewport ensures the coordinates the VLM outputs map 1:1 with the browser screen.
- **`navigate_to_url(url)`**: Triggers a page load. We wait for `networkidle` to ensure asynchronous resources (like JS frameworks) finish rendering before the AI takes a look. This includes aggressive error handling to prevent the script from crashing if a site blocks the bot.
- **`close_browser()`**: Safely tears down the page, browser, and playwright instance in that specific order to prevent zombie processes.

### Vision & Screenshots (`screenshot.py`)
- **`take_screenshot()`**: Captures a full `1280x720` PNG of the current page state, saves it to disk for debugging, and converts it to a JPEG-compressed Base64 string. 
- *Note:* We deliberately do not resize the image dimensionally. Feeding the original `1280x720` image to the model ensures maximum coordinate accuracy. We only use JPEG compression to save on network payload size.

### Interaction Tools (`mouse.py`, `keyboard.py`, `scroll.py`, `wait.py`)
These tools are exposed directly to the AI model via JSON schema.
- They validate that the browser is open.
- They wrap Playwright commands (e.g. `page.mouse.click`, `page.keyboard.type`) in `try...except` blocks to prevent the agent from dying due to an invalid interaction.
- They return a natural language string (e.g. `"Clicked at (x, y)"`) which is fed back into the AI's conversation history so it knows the action succeeded.

---

## 3. The Agent Loop (`src/agent/agent.py`)

The `run_agent()` function is the brain of the operation. It executes a maximum of 25 steps to prevent infinite loops.

### The Perception-Action Cycle:
1. **See**: The agent takes a screenshot (`take_screenshot()`).
2. **Think**: The screenshot and the conversation history are sent to the VLM. The prompt instructs the model to use *Chain-of-Thought* reasoning (analyzing the image, locating the target, estimating bounding boxes) before outputting a decision.
3. **Act**: The VLM outputs a JSON object requesting a tool call (e.g. `click_on_screen`).
4. **Execute**: `execute_tool()` parses the JSON, looks up the corresponding Python function in the `TOOLS` dictionary, and runs it.
5. **Observe**: The string result of the tool execution is appended to the message history, and the loop repeats.

### Memory Management (`strip_old_images`)
The HuggingFace Inference API has a strict limit of 5 images per request. If we pass the entire visual history of the session, the API will reject the request. 
To solve this, `strip_old_images()` runs at the start of every cycle. It iterates backward through the conversation history and removes the Base64 image payloads from all turns except the absolute most recent one. The AI retains the *textual* history of what it did, but only sees the *current* visual state.

### Anti-Stuck Mechanisms
- **Loop Detection**: The agent hashes its current action. If it repeats the exact same action 3 times in a row, the loop injects a warning message into the context to nudge the AI to try something else. After 5 times, it forcefully aborts to save tokens.
- **Browser Death Guard**: Before taking a screenshot, it checks `state.page.is_closed()`. If the page died (e.g. anti-bot protection kicked in), it halts immediately.

---

## 4. The System Prompt (`src/agent/prompt.py`)
Because the HuggingFace router does not natively support OpenAI's strict `tools` schema for Qwen2.5-VL, we employ "JSON-in-text" prompting.
- The prompt establishes the strict `1280x720` coordinate system.
- It enforces a workflow rule: *Always click a field before typing into it*.
- It embeds 4 realistic "few-shot" examples that show the model exactly how to reason about an image and format its JSON output.
