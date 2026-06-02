# Tools Reference — Web Automation Agent

> Complete reference for every tool (function) the AI can call to control the browser.

---

## Overview

Tools are the hands of the agent — they let the AI take real actions in the browser. When the AI decides what to do next, it responds with a **tool call**: a structured message specifying which function to call and with what arguments.

The agent framework receives that tool call, executes the corresponding Python function, and feeds the result back into the conversation so the AI can see what happened.

### How Tools Work

```
AI Response:
{
  "tool_calls": [{
    "function": {
      "name": "click_on_screen",
      "arguments": "{\"x\": 640, \"y\": 385}"
    }
  }]
}
          │
          ▼
execute_tool("click_on_screen", {"x": 640, "y": 385})
          │
          ▼
mouse.click_on_screen(x=640, y=385)
          │
          ▼
Returns: "Clicked at (640, 385)"
          │
          ▼
Appended to conversation history as tool message
```

### Tool Design Rules

Every tool in this project follows the same contract:

| Rule | Reason |
|------|--------|
| Returns a plain string | The AI reads the result; strings are universally parseable |
| Guards against missing browser | Prevents cryptic Python errors; gives AI a useful error message |
| Catches all exceptions | The loop must never crash; errors become AI-readable strings |
| Has a JSON schema in `prompt.py` | The AI learns how to call it from these schemas |

### Coordinate System

Mouse tools use pixel coordinates relative to the browser window:

```
(0,0) ─────────────────────────── (1280,0)
  │                                    │
  │         Browser Window             │
  │          1280 × 720 px             │
  │                                    │
(0,720) ────────────────────────(1280,720)
```

- `x` = horizontal position (0 = left edge, 1280 = right edge)
- `y` = vertical position (0 = top edge, 720 = bottom edge)
- Center of screen = `(640, 360)`

---

## Tool Index

| # | Tool Name | Category | Source File |
|---|-----------|----------|-------------|
| 1 | [`click_on_screen`](#1-click_on_screen) | Mouse | `src/tools/mouse.py` |
| 2 | [`double_click`](#2-double_click) | Mouse | `src/tools/mouse.py` |
| 3 | [`send_keys`](#3-send_keys) | Keyboard | `src/tools/keyboard.py` |
| 4 | [`scroll`](#4-scroll) | Scroll | `src/tools/scroll.py` |
| 5 | [`open_browser`](#5-open_browser) | Browser | `src/tools/browser.py` |
| 6 | [`navigate_to_url`](#6-navigate_to_url) | Browser | `src/tools/browser.py` |
| 7 | [`take_screenshot`](#7-take_screenshot) | Vision | `src/tools/screenshot.py` |

---

## 1. `click_on_screen`

**Source file:** `src/tools/mouse.py`

### Description

Moves the mouse cursor to the specified (x, y) coordinates and performs a single left-click. This is the most commonly used tool — used for clicking buttons, selecting form fields, activating checkboxes, navigating links, and interacting with any clickable UI element.

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `x` | `int` | ✅ Yes | Horizontal pixel coordinate (0–1280) |
| `y` | `int` | ✅ Yes | Vertical pixel coordinate (0–720) |

### Return Value

| Outcome | Return String |
|---------|--------------|
| Success | `"Clicked at (x, y)"` |
| Browser not open | `"Error: Browser is not open. Call open_browser() first."` |
| Playwright error | `"Error clicking: <error message>"` |

### When the AI Uses It

- **Clicking into a text input field** — to move the cursor focus there before typing
- **Clicking a button** — Submit, Next, OK, Login, etc.
- **Clicking a link** — to navigate to another page
- **Clicking a checkbox or radio button** — to toggle its state
- **Clicking a dropdown menu** — to open it
- **Dismissing a modal** — clicking the X or Cancel button

### Example AI Tool Call

```json
{
  "function": {
    "name": "click_on_screen",
    "arguments": "{\"x\": 640, \"y\": 385}"
  }
}
```

### JSON Schema (as seen by the AI)

```json
{
  "type": "function",
  "function": {
    "name": "click_on_screen",
    "description": "Click at the specified (x, y) pixel coordinates on the browser screen.",
    "parameters": {
      "type": "object",
      "properties": {
        "x": { "type": "integer", "description": "Horizontal pixel coordinate" },
        "y": { "type": "integer", "description": "Vertical pixel coordinate" }
      },
      "required": ["x", "y"]
    }
  }
}
```

---

## 2. `double_click`

**Source file:** `src/tools/mouse.py`

### Description

Performs a double-click at the specified (x, y) coordinates. A double-click is two rapid left-clicks in succession at the same position. Useful for selecting all text in an input field or opening items that require double-clicking.

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `x` | `int` | ✅ Yes | Horizontal pixel coordinate (0–1280) |
| `y` | `int` | ✅ Yes | Vertical pixel coordinate (0–720) |

### Return Value

| Outcome | Return String |
|---------|--------------|
| Success | `"Double-clicked at (x, y)"` |
| Browser not open | `"Error: Browser is not open. Call open_browser() first."` |
| Playwright error | `"Error double-clicking: <error message>"` |

### When the AI Uses It

- **Selecting all text in an input field** — double-clicking a word selects it; the AI can then overwrite it with `send_keys`
- **Replacing existing values** — if a field already has text and the AI needs to replace it, double-click to select + type to replace
- **UI elements that respond to double-click** — some web apps require double-click to activate an item

### Difference from `click_on_screen`

| Feature | `click_on_screen` | `double_click` |
|---------|------------------|---------------|
| Click count | 1 | 2 (rapid) |
| Common use | Focus, navigate, toggle | Select text, open items |
| Playwright call | `mouse.click()` | `mouse.dblclick()` |

### Example AI Tool Call

```json
{
  "function": {
    "name": "double_click",
    "arguments": "{\"x\": 400, \"y\": 200}"
  }
}
```

---

## 3. `send_keys`

**Source file:** `src/tools/keyboard.py`

### Description

Types a string of text into the browser at the current cursor position. Uses Playwright's keyboard simulation to type each character one by one, exactly as a human would. The browser must have a focused input element (i.e., the AI should call `click_on_screen` on a text field first).

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `text` | `str` | ✅ Yes | The text string to type |

### Return Value

| Outcome | Return String |
|---------|--------------|
| Success | `"Typed: '<text>'"` |
| Browser not open | `"Error: Browser is not open. Call open_browser() first."` |
| Playwright error | `"Error sending keys: <error message>"` |

### When the AI Uses It

- **Filling in form fields** — names, emails, phone numbers, addresses
- **Entering search queries** — typing into a search bar
- **Writing messages or comments** — filling in textarea elements
- **Typing keyboard shortcuts** — e.g., `"Enter"` to submit, `"Tab"` to move between fields

### Special Keys

Playwright's `keyboard.type()` handles most printable characters automatically. For special keys, the AI may combine `send_keys` with Playwright's key press mechanism. Common special key strings:

| What to type | String to pass |
|-------------|---------------|
| Enter/Return | `"\n"` or `"Enter"` |
| Tab | `"\t"` |
| Backspace | `"\b"` |

### Example AI Tool Call

```json
{
  "function": {
    "name": "send_keys",
    "arguments": "{\"text\": \"alex@email.com\"}"
  }
}
```

### Typical Usage Pattern

The AI almost always uses `click_on_screen` before `send_keys`:

```
Step N:   click_on_screen(x=400, y=200)   ← Focus the email field
Step N+1: send_keys("alex@email.com")      ← Type into it
```

---

## 4. `scroll`

**Source file:** `src/tools/scroll.py`

### Description

Scrolls the browser page vertically. Used when content the AI needs to interact with is outside the visible viewport — either above or below the current scroll position.

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `direction` | `str` | ✅ Yes | `"up"` or `"down"` |
| `amount` | `int` | ✅ Yes | Number of pixels to scroll |

### Return Value

| Outcome | Return String |
|---------|--------------|
| Success | `"Scrolled down 300 pixels"` / `"Scrolled up 300 pixels"` |
| Invalid direction | `"Error: direction must be 'up' or 'down'"` |
| Browser not open | `"Error: Browser is not open. Call open_browser() first."` |
| Playwright error | `"Error scrolling: <error message>"` |

### When the AI Uses It

- **Reaching elements below the fold** — forms with many fields often extend beyond the visible window
- **Scrolling past cookie banners** — popups at the top or bottom of the page
- **Viewing confirmation messages** — success messages after submitting may appear lower on the page
- **Exploring long pages** — when the AI doesn't immediately see what it's looking for

### Typical Scroll Amounts

| Use Case | Suggested Amount |
|----------|-----------------|
| One "screen" down | `300–500` px |
| Small nudge | `100–150` px |
| Large jump | `700–1000` px |

### Example AI Tool Call

```json
{
  "function": {
    "name": "scroll",
    "arguments": "{\"direction\": \"down\", \"amount\": 300}"
  }
}
```

### How It Works Internally

Playwright's `page.evaluate()` runs JavaScript in the browser:
```javascript
window.scrollBy(0, 300);   // positive = down
window.scrollBy(0, -300);  // negative = up
```

---

## 5. `open_browser`

**Source file:** `src/tools/browser.py`

### Description

Launches a Chromium browser instance and creates a new page (tab). Stores the browser and page objects in the shared `state` singleton so all other tools can access them. This is always the first tool called in any session.

### Parameters

*None — this function takes no arguments.*

### Return Value

| Outcome | Return String |
|---------|--------------|
| Success | `"Browser opened successfully"` |
| Already open | `"Browser is already open"` |
| Playwright error | `"Error opening browser: <error message>"` |

### When the AI Uses It

- **Always first** — Before any other browser action can be taken, the browser must be open
- **Recovery** — If a tool returns an error saying "Browser is not open," the AI knows to call this first
- Typically called once at the start of `run_agent()` (not by the AI mid-task, but available as a tool for self-correction)

### What It Does Internally

```python
state.playwright = await async_playwright().start()
state.browser = await state.playwright.chromium.launch(headless=False)
state.page = await state.browser.new_page()
await state.page.set_viewport_size({"width": 1280, "height": 720})
```

- `headless=False` = browser window is visible on your screen
- Viewport is set to 1280×720 so screenshot coordinates are consistent

### Example AI Tool Call

```json
{
  "function": {
    "name": "open_browser",
    "arguments": "{}"
  }
}
```

---

## 6. `navigate_to_url`

**Source file:** `src/tools/browser.py`

### Description

Navigates the browser to a specified URL. Waits for the page to fully load (`networkidle` state) before returning, so the AI won't take a screenshot of a half-loaded page.

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `url` | `str` | ✅ Yes | The full URL to navigate to (must include `http://` or `https://`) |

### Return Value

| Outcome | Return String |
|---------|--------------|
| Success | `"Navigated to <url>"` |
| Browser not open | `"Error: Browser is not open. Call open_browser() first."` |
| Network/timeout error | `"Error navigating: <error message>"` |

### When the AI Uses It

- **Initial navigation** — Going to the starting URL of the task (typically called by `run_agent()` before the loop)
- **Multi-page flows** — If a task requires navigating to a second page (e.g., going to a confirmation page)
- **Recovery** — If the page ended up in a wrong state, the AI can navigate back to the correct URL

### Wait Strategy

The function waits for `networkidle` — meaning it waits until there are no more network requests in flight for at least 500ms. This ensures:
- JavaScript has had time to run
- Dynamic content has loaded
- Forms and inputs are interactive

### Example AI Tool Call

```json
{
  "function": {
    "name": "navigate_to_url",
    "arguments": "{\"url\": \"https://example.com/contact\"}"
  }
}
```

---

## 7. `take_screenshot`

**Source file:** `src/tools/screenshot.py`

### Description

Captures the current state of the browser window as an image. Compresses it for efficiency and returns it as a base64-encoded JPEG string. This tool is called **automatically at the beginning of every loop step** by the agent — it's how the AI "sees" the current state of the browser.

### Parameters

*None — this function takes no arguments.*

### Return Value

| Outcome | Return Value |
|---------|-------------|
| Success | Base64-encoded JPEG string (data URL format) |
| Browser not open | `"Error: Browser is not open."` |
| Pillow/IO error | `"Error taking screenshot: <error message>"` |

The successful return is a long string starting with:
```
data:image/jpeg;base64,/9j/4AAQSkZJRgAB...
```

This string is then embedded directly into the AI API request as an image message.

### When the AI Uses It

- **Automatically every step** — The agent framework always takes a screenshot before calling the AI; the AI doesn't explicitly call this tool itself
- **Available to AI if needed** — The AI could theoretically request a fresh screenshot mid-reasoning, but this is rare

### Compression Pipeline

The raw screenshot is heavily compressed before being sent to the AI:

```
Playwright page.screenshot()
    ↓
PNG bytes in memory (~500 KB for 1280×720)
    ↓
Image.open() via Pillow
    ↓
Resize to 640×360 (half dimensions = quarter pixels)
    ↓
Save as JPEG at quality=60
    ↓
~30 KB compressed image
    ↓
base64.b64encode() → string for JSON transport
```

### Why Not Send Full Resolution?

| Image | Size | Approx. API Tokens | Cost Impact |
|-------|------|-------------------|-------------|
| 1280×720 PNG | ~500 KB | ~750K tokens | $$$ |
| 640×360 JPEG q60 | ~30 KB | ~45K tokens | $ |

At 25 steps per task, the savings add up significantly. The 640×360 resolution is sufficient for the AI to read text, identify UI elements, and determine coordinates.

### Example AI Tool Call

```json
{
  "function": {
    "name": "take_screenshot",
    "arguments": "{}"
  }
}
```

---

## Adding a New Tool

To add a new tool to the agent:

### Step 1: Write the function

Create the async function in the appropriate file (or create a new file in `src/tools/`):

```python
# src/tools/my_tool.py
from .state import state

async def my_new_tool(param: str) -> str:
    if state.page is None:
        return "Error: Browser is not open."
    try:
        # do something with state.page
        return f"Success: did the thing with {param}"
    except Exception as e:
        return f"Error: {str(e)}"
```

### Step 2: Add the JSON schema to `prompt.py`

```python
# src/agent/prompt.py — append to TOOL_SCHEMAS list
{
    "type": "function",
    "function": {
        "name": "my_new_tool",
        "description": "Does the new thing with the given param.",
        "parameters": {
            "type": "object",
            "properties": {
                "param": {
                    "type": "string",
                    "description": "The thing to do"
                }
            },
            "required": ["param"]
        }
    }
}
```

### Step 3: Register in `execute_tool()` in `agent.py`

```python
# src/agent/agent.py — in the execute_tool() dispatcher
elif tool_name == "my_new_tool":
    return await my_new_tool(args["param"])
```

### Step 4: Import the function

```python
# src/agent/agent.py — add to imports
from tools.my_tool import my_new_tool
```

The AI will now be able to call `my_new_tool` in its tool responses.
