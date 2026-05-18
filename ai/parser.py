import json
import logging
import re
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

# ── Keyword maps for local fallback parser ──────────────────────────────────
_CATEGORY_KEYWORDS = {
    "餐饮": ["餐", "饭", "食", "lunch", "dinner", "breakfast", "早餐", "午餐", "晚餐",
             "麦当劳", "kfc", "肯德基", "pizza", "burger", "coffee", "咖啡", "茶",
             "mamak", "kopitiam", "restaurant", "cafe", "食堂", "canteen", "hawker",
             "nasi", "mee", "rice", "chicken", "beef", "pork", "fish"],
    "交通": ["grab", "uber", "taxi", "mrt", "lrt", "bus", "toll", "petrol", "fuel",
             "parking", "park", "油", "停车", "巴士", "地铁", "touchngo", "tng"],
    "购物": ["shop", "mall", "buy", "购", "买", "supermarket", "pasar", "market",
             "lazada", "shopee", "amazon", "guardian", "watson", "pharmacy", "药"],
    "医疗": ["clinic", "hospital", "doctor", "医", "药", "medicine", "health"],
    "住宿": ["hotel", "airbnb", "rent", "房", "住", "accommodation"],
    "水电": ["electric", "water", "internet", "wifi", "phone", "bill", "telco",
             "unifi", "maxis", "celcom", "digi", "电", "水", "网"],
    "娱乐": ["movie", "cinema", "game", "entertainment", "karaoke", "gym", "sport",
             "电影", "游戏", "娱乐"],
}

_CURRENCY_PATTERNS = [
    (r'\bRM\s*(\d+(?:\.\d{1,2})?)', "MYR"),
    (r'(\d+(?:\.\d{1,2})?)\s*RM\b', "MYR"),
    (r'\bMYR\s*(\d+(?:\.\d{1,2})?)', "MYR"),
    (r'\$(\d+(?:\.\d{1,2})?)', "USD"),
    (r'(\d+(?:\.\d{1,2})?)\s*(?:块|元|ringgit|ringgit)', "MYR"),
    (r'(\d+(?:\.\d{1,2})?)', "MYR"),   # bare number → default MYR
]


def _local_parse(text: str) -> dict | None:
    """Fast local parser — no AI needed. Handles common phrases like
    '午餐麦当劳11块钱', 'grab 12.50', 'KFC RM15'."""
    text_lower = text.lower()

    # 1. Extract amount + currency
    amount = None
    currency = "MYR"
    for pattern, cur in _CURRENCY_PATTERNS:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            try:
                amount = float(m.group(1))
                currency = cur
                break
            except (ValueError, IndexError):
                continue
    if amount is None:
        return None

    # 2. Detect category from keywords
    category = "其他"
    for cat, keywords in _CATEGORY_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            category = cat
            break

    # 3. Extract merchant — remove amount/currency/common filler words
    merchant_text = re.sub(
        r'RM\s*[\d.]+|[\d.]+\s*(?:RM|块钱?|元|ringgit)?|'
        r'\b(?:午餐|晚餐|早餐|lunch|dinner|breakfast|吃|买|花了|花|共|总共|一共|约)\b',
        ' ', text, flags=re.IGNORECASE
    ).strip()
    merchant_text = re.sub(r'\s+', ' ', merchant_text).strip('., ')
    merchant = merchant_text if merchant_text else "Unknown"

    return {
        "date": date.today().isoformat(),
        "amount": amount,
        "currency": currency,
        "merchant": merchant,
        "category": category,
        "note": "",
        "source": "文字",
    }


def parse_expense_text(text: str) -> dict | None:
    # Try Gemini first; fall back to local parser if Gemini fails/quota exceeded
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
            logger.info("[parser] Gemini returned error, trying local parser")
            return _local_parse(text)
        data["source"] = "文字"
        return data
    except Exception as e:
        logger.warning("[parser] Gemini failed (%s: %s), falling back to local parser", type(e).__name__, e)
        return _local_parse(text)
