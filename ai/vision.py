import json
import logging

from utils import ssl_patch
ssl_patch.apply()

import google.generativeai as genai
from config import GOOGLE_GEMINI_API_KEY, EXPENSE_CATEGORIES

genai.configure(api_key=GOOGLE_GEMINI_API_KEY, transport="rest")

logger = logging.getLogger(__name__)

_PROMPT = f"""Analyze this receipt image and extract expense information.
Return ONLY valid JSON with these exact keys:
- date: string in YYYY-MM-DD format (use today if not visible)
- amount: number (total amount paid)
- currency: 3-char ISO code (e.g. MYR, USD, SGD)
- merchant: string (shop/restaurant name)
- category: one of {EXPENSE_CATEGORIES}
- note: string (empty string if nothing notable)

If you cannot read the receipt clearly, return: {{"error": "cannot read receipt"}}
Do not include any text outside the JSON object."""


def _detect_mime_type(image_bytes: bytes) -> str:
    """Detect image MIME type from magic bytes."""
    if image_bytes[:8] == b'\x89PNG\r\n\x1a\n':
        return "image/png"
    if image_bytes[:3] == b'GIF':
        return "image/gif"
    if image_bytes[:4] == b'RIFF' and image_bytes[8:12] == b'WEBP':
        return "image/webp"
    # WebP without RIFF header check
    if len(image_bytes) > 12 and image_bytes[8:12] == b'WEBP':
        return "image/webp"
    return "image/jpeg"  # default for JPEG / unknown


def analyze_receipt(image_bytes: bytes) -> dict | None:
    try:
        model = genai.GenerativeModel("gemini-2.0-flash")
        mime_type = _detect_mime_type(image_bytes)
        logger.debug("[vision] detected MIME type: %s, size: %d bytes", mime_type, len(image_bytes))
        image_part = {"mime_type": mime_type, "data": image_bytes}
        response = model.generate_content([_PROMPT, image_part])
        raw = response.text.strip()
        logger.debug("[vision] raw Gemini response: %s", raw)
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        data = json.loads(raw)
        if "error" in data:
            logger.info("[vision] Gemini returned error: %s", data)
            return None
        data["source"] = "图片"
        return data
    except Exception as e:
        logger.error("[vision] analyze_receipt failed: %s: %s", type(e).__name__, e)
        return None
