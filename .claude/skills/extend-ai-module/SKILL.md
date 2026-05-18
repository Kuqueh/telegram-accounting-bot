---
name: extend-ai-module
description: Use when adding a new AI provider (e.g. OpenAI, Claude), swapping Gemini for another model, adding a new processing mode (e.g. PDF receipts, URL parsing), or modifying how expense data is extracted from images or text.
---

# Extend AI Module

## Overview

All AI modules follow the same contract: **one function, one return type**. Add a new file in `ai/`, write tests first, wire into handlers. Nothing else changes.

## The AI Module Contract

Every function in `ai/` must return either a valid `ExpenseRecord` dict or `None`:

```python
# For image/audio/text → expense extraction
def my_function(input: bytes | str) -> dict | None:
    try:
        # call AI API
        # parse response
        result["source"] = "your_source_label"  # 图片 | 语音 | 文字 | etc.
        return result
    except Exception:
        return None   # ALWAYS catch-all → None, never raise
```

**ExpenseRecord keys:** `date` (YYYY-MM-DD), `amount` (float), `currency` (3-char), `merchant` (str), `category` (one of `EXPENSE_CATEGORIES`), `note` (str), `source` (str)

## Adding a New AI Module

### 1. Create `ai/{name}.py`

```python
import json
import google.generativeai as genai          # or import openai, anthropic, etc.
from config import GOOGLE_GEMINI_API_KEY, EXPENSE_CATEGORIES

# configure at module level
genai.configure(api_key=GOOGLE_GEMINI_API_KEY)

def analyze_pdf_receipt(pdf_bytes: bytes) -> dict | None:
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        # ... call API ...
        data = json.loads(response.text.strip())
        if "error" in data:
            return None
        data["source"] = "PDF"
        return data
    except Exception:
        return None
```

### 2. Write tests first (`tests/test_{name}.py`)

Mock pattern — copy from any existing test file:

```python
from unittest.mock import MagicMock, patch
from ai.your_module import your_function

@pytest.fixture
def mock_gemini():
    with patch("ai.your_module.genai.GenerativeModel") as mock_cls:
        mock_model = MagicMock()
        mock_cls.return_value = mock_model
        yield mock_model

def test_happy_path(mock_gemini):
    mock_gemini.generate_content.return_value.text = '{"date":"2026-05-18","amount":45.5,"currency":"MYR","merchant":"KFC","category":"餐饮","note":""}'
    result = your_function(b"fake_input")
    assert result["source"] == "your_label"
    assert result["amount"] == 45.5

def test_api_error_returns_none(mock_gemini):
    mock_gemini.generate_content.side_effect = Exception("timeout")
    assert your_function(b"any") is None
```

Run: `venv\Scripts\python -m pytest tests/test_{name}.py -v` — watch it fail first.

### 3. Wire into `bot/handlers.py`

Import and call your new function following the existing handler pattern:

```python
from ai.your_module import your_function

async def handle_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("🔍 正在分析...")
    # download file → call your_function → check None → append_record → reply
```

### 4. Register new handler in `main.py` if needed

```python
app.add_handler(MessageHandler(filters.Document.PDF, handle_pdf))
```

## Swapping an Existing Provider

To replace Gemini with OpenAI in `ai/vision.py`:
1. Change imports and configure `openai` client
2. Update the API call inside `analyze_receipt()`
3. Keep the function signature and return type **identical**
4. Tests should still pass unchanged (they mock at the function level)

## Prompt Engineering Tips

Always end prompts with:
```
Return ONLY valid JSON. Do not include text outside the JSON object.
If you cannot extract data, return: {"error": "reason"}
```

Strip markdown code fences from responses:
```python
if raw.startswith("```"):
    raw = raw.split("```")[1]
    if raw.startswith("json"):
        raw = raw[4:]
```

## Expense Categories

Import from config: `from config import EXPENSE_CATEGORIES`

```python
["餐饮", "购物", "交通", "娱乐", "医疗", "住宿", "水电", "其他"]
```

Always include this list in AI prompts so the model picks the right category.
