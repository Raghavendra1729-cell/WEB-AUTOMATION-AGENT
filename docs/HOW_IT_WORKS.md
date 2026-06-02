# How It Works — Web Automation Agent

> A beginner-friendly, plain-English guide to understanding the Web Automation Agent from the ground up.

---

## Table of Contents

1. [What Is an AI Agent?](#1-what-is-an-ai-agent)
2. [What Is a Vision Model?](#2-what-is-a-vision-model)
3. [How This Project Combines Both](#3-how-this-project-combines-both)
4. [A Full Example — Step by Step](#4-a-full-example--step-by-step)
5. [What Happens When You Run `python src/main.py`](#5-what-happens-when-you-run-python-srcmainpy)
6. [What Each File Does — Plain English](#6-what-each-file-does--plain-english)
7. [Common Questions Answered](#7-common-questions-answered)

---

## 1. What Is an AI Agent?

Imagine you asked a smart assistant to do something for you: *"Book me a table at a restaurant for Saturday."*

A regular chatbot would just reply with text. An **AI agent** would actually *do* it — it would:
1. Open a browser
2. Go to a restaurant booking website
3. Fill in the date and number of guests
4. Click the confirm button
5. Tell you "Done! Table booked for Saturday at 7pm."

The key difference is that an agent **takes actions** in the real world, not just responds with words.

Agents work in a loop:
```
┌─────────────────────────────────────────────────┐
│                                                 │
│   Observe → Think → Act → Observe → Think → …  │
│                                                 │
└─────────────────────────────────────────────────┘
```

- **Observe:** Look at the current state of the world (in our case: take a screenshot)
- **Think:** Ask the AI "what should I do next?"
- **Act:** Do what the AI says (click, type, scroll)
- **Repeat** until the task is done

---

## 2. What Is a Vision Model?

Most AI models only understand text. You type words in, you get words back.

A **vision model** understands both images *and* text. You can show it a picture and ask a question about it:

> "Here's a screenshot of a webpage. Where is the 'Submit' button?"

The model can *see* the image, understand what's in it, and give you a useful answer.

The vision model we use is called **Qwen2.5-VL-72B-Instruct**. The "VL" stands for "Vision-Language." It was trained on billions of images and text, so it's very good at understanding screenshots of websites, apps, and documents.

The "72B" means it has 72 billion parameters — it's a very large, capable model.

---

## 3. How This Project Combines Both

This project puts the two ideas together:

1. **Vision model** = the AI that can *see* the screen and decide what to do
2. **AI agent** = the loop that repeatedly takes screenshots and executes the AI's decisions

```
┌────────────────────────────────────────────────────────────────┐
│                      Every Step:                               │
│                                                                │
│  📸 Screenshot  →  🤖 AI thinks  →  🖱️ Click/Type/Scroll      │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

Think of it like a human sitting in front of a computer:
- The human *looks* at the screen (screenshot)
- The human *decides* what to do (AI)
- The human *moves their hand* to act (Playwright browser control)

The difference is this happens programmatically, at computer speed, driven by AI.

---

## 4. A Full Example — Step by Step

Let's say the task is: **"Fill out the contact form with name 'Alex' and email 'alex@email.com'"**

The starting URL is a webpage with a contact form.

---

### Step 1: Browser Opens

The program launches a real Chromium browser window (you'll see it pop up on your screen) and navigates to the contact form page.

```
🌐 Browser opens → Goes to https://example.com/contact
```

---

### Step 2: First Screenshot

The agent takes a screenshot of the current state of the browser. It compresses this image (to save money on API costs) and prepares it to send to the AI.

```
📸 Screenshot taken → Compressed to 640×360 JPEG
```

The screenshot might look something like this:

```
┌─────────────────────────────────────────┐
│  Contact Us                             │
│                                         │
│  Name:  [                          ]    │
│                                         │
│  Email: [                          ]    │
│                                         │
│  Message: [                        ]    │
│                                         │
│         [ Submit ]                      │
└─────────────────────────────────────────┘
```

---

### Step 3: Ask the AI

The agent sends this message to the AI:

> "Here is a screenshot of the browser. Your task is: Fill out the contact form with name 'Alex' and email 'alex@email.com'. What should you do next?"

Along with this, it includes a list of available tools the AI can use:
- `click_on_screen(x, y)`
- `send_keys(text)`
- `scroll(direction, amount)`
- etc.

---

### Step 4: AI Responds with a Tool Call

The AI looks at the screenshot, sees the Name field, and responds:

```json
{
  "tool": "click_on_screen",
  "arguments": { "x": 400, "y": 200 }
}
```

(It figured out roughly where the Name input box is on the screen.)

---

### Step 5: Execute the Action

The program calls `click_on_screen(400, 200)`, which tells Playwright to move the mouse and click at that position in the browser.

The Name field is now focused (you'd see a blinking cursor there).

---

### Step 6: Loop Continues

Next iteration — new screenshot taken (showing the Name field is now focused), sent to AI again.

AI responds: `send_keys("Alex")`

Program types "Alex" into the field.

---

### Steps 7–10: Continue Until Done

The process repeats:
- Click the Email field
- Type "alex@email.com"
- Click the Submit button

On the final step, when the AI sees the form has been submitted (maybe there's a success message), it responds with just the word **"DONE"** instead of a tool call.

---

### Step 11: Browser Closes

The loop detects "DONE" and exits. The browser closes. Done!

---

## 5. What Happens When You Run `python src/main.py`

Here's a timeline of everything that happens, in order:

```
T=0s    python src/main.py runs
        │
T=0.1s  .env file is read → HF_API_TOKEN loaded
        │
T=0.2s  Playwright starts → Chromium browser window appears
        │
T=1.0s  Browser navigates to START_URL
        │
T=1.5s  ┌─── LOOP STEP 1 ──────────────────────────────────────────┐
        │   Screenshot taken, compressed                            │
        │   HTTP POST → api.huggingface.co (AI call, ~2-5 seconds) │
        │   AI returns: click_on_screen(x=300, y=250)              │
        │   Playwright clicks at (300, 250)                         │
        └──────────────────────────────────────────────────────────┘
        │
T=8s    ┌─── LOOP STEP 2 ──────────────────────────────────────────┐
        │   Screenshot taken (field is now active)                  │
        │   HTTP POST → HuggingFace API                            │
        │   AI returns: send_keys("Alex")                          │
        │   Playwright types "Alex"                                 │
        └──────────────────────────────────────────────────────────┘
        │
        ... (continues) ...
        │
T=60s   AI responds: "DONE"
        Loop exits
        │
T=60.1s Browser closes
        Program exits
```

**Console output** — you'll see colored log messages like:
```
[17:30:01] INFO  Agent started. Task: Fill out contact form...
[17:30:02] INFO  Browser opened
[17:30:03] INFO  Navigated to https://example.com/contact
[17:30:04] INFO  Step 1: Taking screenshot...
[17:30:08] TOOL  AI called: click_on_screen(x=300, y=250)
[17:30:09] INFO  Tool result: Clicked at (300, 250)
[17:30:10] INFO  Step 2: Taking screenshot...
[17:30:14] TOOL  AI called: send_keys(text='Alex')
...
[17:31:02] INFO  AI signaled DONE. Task complete.
[17:31:02] INFO  Browser closed.
```

---

## 6. What Each File Does — Plain English

### `src/main.py`
**The starting point.** You edit this file to change what task the agent performs and which URL it starts at. It just defines those two things and then calls `run_agent()` to hand off control.

---

### `src/agent/agent.py`
**The brain.** This file contains the main loop — the "observe → think → act" cycle. It manages the conversation history, calls the AI API, reads the AI's response, and runs the appropriate tool. If the AI says "DONE," this file stops the loop.

---

### `src/agent/prompt.py`
**The instruction manual.** This tells the AI what it's supposed to do and how. It has two parts:
- The **system prompt** — a paragraph explaining to the AI that it's a web automation agent and should use tools to complete tasks
- The **tool schemas** — JSON descriptions of every available tool (what it's called, what parameters it takes, what it does)

Without this file, the AI wouldn't know it has tools available to use.

---

### `src/tools/state.py`
**The shared memory.** Playwright creates a browser, which creates a page (tab). Those objects need to be accessible from many different files. This file creates a single `state` object that everyone can import and use. Think of it as a shared whiteboard.

---

### `src/tools/browser.py`
**The browser manager.** Opens and closes the browser. When `open_browser()` runs, it starts Playwright, launches Chromium, and saves the browser + page objects into the shared `state`. When `close_browser()` runs, it cleans everything up.

---

### `src/tools/screenshot.py`
**The camera.** Every step, this takes a photo of the browser window, shrinks it down (to save on AI costs), and converts it to a format that can be sent in an HTTP request. This is what gives the AI its "eyes."

---

### `src/tools/mouse.py`
**The mouse.** Lets the AI move and click the mouse anywhere on the browser screen. Coordinates are in pixels — (0,0) is the top-left corner, and the window is 1280×720 pixels.

---

### `src/tools/keyboard.py`
**The keyboard.** Types text into the browser at wherever the cursor currently is. The AI typically clicks on an input field first, then uses this to type into it.

---

### `src/tools/scroll.py`
**The scroll wheel.** Scrolls the page up or down. Needed when content is below the fold (not visible in the current viewport).

---

### `src/utils/config.py`
**The settings loader.** Reads the `.env` file to get your HuggingFace API token. This keeps secrets out of the source code.

---

### `src/utils/logger.py`
**The reporter.** Prints colored, timestamped messages to the terminal so you can follow what the agent is doing in real time.

---

## 7. Common Questions Answered

### Q: Does the agent actually open a real browser?

**Yes.** Playwright launches a real Chromium browser — the same engine that powers Google Chrome. You'll see a browser window open on your screen. The agent's mouse and keyboard actions happen in that real browser, just like a human using it.

---

### Q: Can I watch it work?

**Yes.** Because the browser is non-headless (visible), you can watch the agent fill in forms, click buttons, and navigate pages in real time. It's quite satisfying to watch.

---

### Q: How does the AI know where to click?

The AI is given a screenshot of the browser window (640×360 pixels). It can look at that image and estimate the pixel coordinates of elements it wants to interact with. For example, if a "Submit" button appears at roughly the center of the page, the AI might say `click_on_screen(x=640, y=480)`.

This isn't pixel-perfect, which is why the AI sees a fresh screenshot after every action — if it clicked slightly off, it can correct on the next step.

---

### Q: What if the AI makes a mistake?

The loop is designed to be self-correcting. If a tool fails, it returns an error message. The AI sees that error in the next step and can try a different approach. For example:

- AI tries to click a button → misses → screenshot shows field wasn't clicked → AI tries again with adjusted coordinates

---

### Q: How long does each step take?

Most of the time is spent waiting for the AI API response — typically **2–5 seconds per step** depending on server load. A 10-step task takes roughly 30–60 seconds.

---

### Q: Can I use a different AI model?

Yes. Since the agent uses HuggingFace's OpenAI-compatible API, you can swap the model name in `agent.py` to any HuggingFace model that supports vision + function calling. The model name format is `"owner/model-name"`.

---

### Q: What if the page changes while the agent is running?

That's fine — and expected. The whole point of taking a new screenshot every step is to always have an up-to-date view of the page. The AI never relies on stale information.

---

### Q: Why not just use Selenium or another automation tool directly?

Traditional automation tools require you to specify *exact* selectors or coordinates upfront:

```python
driver.find_element(By.ID, "email-field").send_keys("test@example.com")
```

This breaks the moment the website changes. Our AI-powered approach is more **flexible and resilient** — the AI looks at the actual screen and adapts, just like a human would.

---

### Q: Is my HuggingFace API token safe?

Your token is stored in a `.env` file that is never committed to git (it's in `.gitignore`). The `config.py` file reads it from there so it never appears in source code.
