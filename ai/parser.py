import json
import logging
from datetime import date

from utils import ssl_patch
ssl_patch.apply()

import google.generativeai as genai
from config import GOOGLE_GEMINI_API_KEY, EXPENSE_CATEGORIES

genai.configure(api_key=GOOGLE_GEMINI_API_KEY, transport="rest")

logger = logging.getLogger(__name__)

_PROMPT_TEMPLATE = (
    "Extract expense information from this text message.\n"
    "Today's date is {today}.\n\n"
    "Return ONLY valid JSON with these exact keys:\n"
    "- date: string in YYYY-MM-DD format\n"
    "- amount: number\n"
    "- currency: 3-char ISO code (default MYR if not mentioned)\n"
    "- merchant: string (shop or payee name, or 'Unknown' if not mentioned)\n"
    f"- category: one of {EXPENSE_CATEGORIES}\n"
    "- note: string (empty string if nothing to add)\n\n"
    "If you cannot extract a valid expense from the text, return: {{\"error\": \"cannot parse\"}}\n"
    "Text: {text}"
)


def parse_expense_text(text: str) -> dict | None:
    try:
        model = genai.GenerativeModel("gemini-2.0-flash")
        prompt = _PROMPT_TEMPLATE.format(today=date.today().isoformat(), text=text)
        response = model.generate_content(prompt)
        raw = response.text.strip()
        logger.debug("[parser] raw Gemini response: %s", raw)
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        data = json.loads(raw)
        if "error" in data:
            logger.info("[parser] Gemini returned error: %s", data)
            return None
        data["source"] = "文字"
        return data
    except Exception as e:
        logger.error("[parser] parse_expense_text failed: %s: %s", type(e).__name__, e)
        return None
