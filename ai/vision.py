import json
import google.generativeai as genai
from config import GOOGLE_GEMINI_API_KEY, EXPENSE_CATEGORIES

genai.configure(api_key=GOOGLE_GEMINI_API_KEY)

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


def analyze_receipt(image_bytes: bytes) -> dict | None:
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        image_part = {"mime_type": "image/jpeg", "data": image_bytes}
        response = model.generate_content([_PROMPT, image_part])
        raw = response.text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        data = json.loads(raw)
        if "error" in data:
            return None
        data["source"] = "图片"
        return data
    except Exception:
        return None
