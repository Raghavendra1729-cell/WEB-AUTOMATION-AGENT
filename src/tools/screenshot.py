"""
src/tools/screenshot.py
-----------------------
Screenshot capture and compression for the Web Automation Agent.

Why this module exists:
    The vision model (Qwen2.5-VL) needs to *see* the current browser state
    at every step.  Playwright can produce a full-resolution PNG, but sending
    a raw 1280×720 PNG over the API on every step would be slow and expensive.

    This module bridges the gap:
      1. Saves the full-resolution PNG locally for debugging / audit trails.
      2. Resizes and JPEG-compresses a copy for the AI, dramatically reducing
         the payload size without losing enough detail to confuse the model.
      3. Returns the compressed image as a base64 string so it can be
         embedded directly in the OpenAI-compatible multimodal message format.

Usage:
    from src.tools.screenshot import take_screenshot
    b64 = await take_screenshot()   # ready to embed in a message
"""

# `io.BytesIO` lets us treat an in-memory byte buffer as if it were a file,
# avoiding the need to write the compressed image to disk.
import io

# `base64` encodes binary image data as ASCII text so it can be embedded
# inside a JSON message payload (the OpenAI API's image_url format).
import base64

# Pillow (PIL) provides resize and re-encode operations.  We use it to
# shrink the screenshot from 1280×720 to 640×360 before JPEG encoding.
from PIL import Image

# The shared browser state — specifically `state.page` for capturing and
# `state.step_count` for sequential file naming.
from src.tools.state import state

# Consistent timestamped logging across all tool modules.
from src.utils.logger import logger


async def take_screenshot() -> str:
    """
    Capture the current browser viewport, persist a full-resolution PNG
    to disk, and return a compressed JPEG as a base64-encoded string.

    Two-copy strategy explained:
        - **Full PNG on disk**: Preserved at original resolution for
          post-run inspection, debugging mis-clicks, and building datasets.
        - **Compressed JPEG in memory**: Halved resolution (640×360) and
          quality=60 JPEG encoding reduces payload to ~10-15 KB, keeping
          API latency and cost low.

    Raises:
        Exception: If no browser page is currently open (`state.page` is
                   None), because there is nothing to screenshot.

    Returns:
        A base64-encoded string of the JPEG-compressed screenshot,
        suitable for embedding as a `data:image/jpeg;base64,…` URL
        in an OpenAI multimodal message.
    """
    # Hard guard — screenshotting without an active page is a programming
    # error, so we raise immediately instead of returning an error string.
    if not state.page:
        raise Exception("Browser page not initialized — call open_browser() first.")

    # Increment before use so the first screenshot is step_001 (1-indexed).
    state.step_count += 1

    # Build a zero-padded filename so screenshots sort correctly in a
    # file browser (step_001.png before step_010.png, etc.).
    filename = f"screenshots/step_{state.step_count:03d}.png"

    # --- 1. Full-resolution capture saved to disk ---
    # `path=filename` tells Playwright to write the PNG directly to disk
    # AND return the raw bytes in the same call — no second read needed.
    png_bytes = await state.page.screenshot(path=filename)
    logger.info(f"Screenshot saved to {filename}")

    # --- 2. Compress for the AI ---
    # Open the in-memory PNG bytes with Pillow.
    img = Image.open(io.BytesIO(png_bytes))

    # Halve the resolution.  The model can still read text and identify
    # UI elements at 640×360 while the payload is ~4× smaller.
    img = img.resize((640, 360))

    # Write the resized image as JPEG into an in-memory buffer.
    # quality=60 strikes a balance: visually readable but small.
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=60)

    # --- 3. Encode to base64 ---
    # `buffer.getvalue()` retrieves the full JPEG bytes.
    # `.decode("utf-8")` converts the base64 bytes to a plain Python string
    # so it can be embedded in a JSON message without further escaping.
    return base64.b64encode(buffer.getvalue()).decode("utf-8")
