# Telegram AI Accounting Bot — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Telegram bot that receives receipt photos, voice messages, or text from users, extracts expense info via Gemini Vision / Groq Whisper, and records each entry to a per-user Google Sheets tab — all using free-tier APIs.

**Architecture:** A long-polling Python process (python-telegram-bot v20) handles incoming messages, dispatches to AI modules (Gemini for vision/text, Groq Whisper for audio), then writes structured records to a shared Google Spreadsheet where each Telegram user gets their own tab. Multi-user isolation is achieved by keying tabs on `user_{telegram_id}`.

**Tech Stack:** Python 3.11, python-telegram-bot 20.x, google-generativeai, groq, gspread, python-dotenv, pytest

---

## File Map

```
C:\cld.dev\telegram-accounting-bot\
├── config.py                  # Load + validate env vars
├── main.py                    # Bot startup, handler registration
├── requirements.txt
├── Procfile                   # Render deployment: worker process
├── .env.example
├── .gitignore
├── ai/
│   ├── __init__.py
│   ├── vision.py              # analyze_receipt(image_bytes) → ExpenseRecord
│   ├── speech.py              # transcribe_voice(audio_bytes) → str
│   └── parser.py             # parse_expense_text(text) → ExpenseRecord
├── sheets/
│   ├── __init__.py
│   └── client.py              # SheetsClient: append, list, delete, summary
├── bot/
│   ├── __init__.py
│   ├── handlers.py            # handle_photo, handle_voice, handle_text
│   ├── commands.py            # /start, /summary, /list, /delete
│   └── keyboards.py           # inline keyboard builders
└── tests/
    ├── conftest.py            # shared fixtures
    ├── test_vision.py
    ├── test_speech.py
    ├── test_parser.py
    └── test_sheets.py
```

**Shared data type** (`ExpenseRecord`) is a plain `dict` with keys:
```python
{
    "date": "2026-05-18",      # str, YYYY-MM-DD
    "amount": 45.50,           # float
    "currency": "MYR",         # str, 3-char ISO
    "merchant": "KFC",         # str
    "category": "餐饮",         # str — one of the 8 categories
    "note": "",                # str, may be empty
    "source": "图片"            # str: 图片 | 语音 | 文字
}
```

---

## Task 1: Project Scaffold

**Files:**
- Create: `requirements.txt`
- Create: `config.py`
- Create: `.env.example`
- Create: `.gitignore`
- Create: `ai/__init__.py`, `sheets/__init__.py`, `bot/__init__.py`, `tests/__init__.py` (all empty)

- [ ] **Step 1: Create the project root and run git init**

```powershell
cd C:\cld.dev\telegram-accounting-bot
git init
```

Expected: `Initialized empty Git repository`

- [ ] **Step 2: Create `requirements.txt`**

```
python-telegram-bot==20.7
google-generativeai==0.8.3
groq==0.12.0
gspread==6.1.2
google-auth==2.29.0
python-dotenv==1.0.1
pytest==8.2.0
pytest-asyncio==0.23.6
```

- [ ] **Step 3: Create `.env.example`**

```
TELEGRAM_BOT_TOKEN=your_botfather_token_here
GOOGLE_GEMINI_API_KEY=your_gemini_api_key_here
GROQ_API_KEY=your_groq_api_key_here
GOOGLE_SHEETS_ID=your_google_sheet_document_id_here
GOOGLE_SERVICE_ACCOUNT_JSON={"type":"service_account","project_id":"..."}
```

- [ ] **Step 4: Create `.gitignore`**

```
.env
venv/
__pycache__/
*.pyc
.pytest_cache/
*.egg-info/
dist/
```

- [ ] **Step 5: Create `config.py`**

```python
import json
import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
GOOGLE_GEMINI_API_KEY = os.environ["GOOGLE_GEMINI_API_KEY"]
GROQ_API_KEY = os.environ["GROQ_API_KEY"]
GOOGLE_SHEETS_ID = os.environ["GOOGLE_SHEETS_ID"]
GOOGLE_SERVICE_ACCOUNT_JSON = json.loads(os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"])

EXPENSE_CATEGORIES = ["餐饮", "购物", "交通", "娱乐", "医疗", "住宿", "水电", "其他"]
SHEET_HEADERS = ["日期", "金额", "货币", "商家", "类别", "备注", "来源"]
```

- [ ] **Step 6: Create empty `__init__.py` files**

```powershell
New-Item -ItemType Directory -Force ai, sheets, bot, tests
@("ai/__init__.py","sheets/__init__.py","bot/__init__.py","tests/__init__.py") | ForEach-Object { New-Item -ItemType File -Path $_ -Force }
```

- [ ] **Step 7: Create virtual environment and install dependencies**

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Expected: All packages install without errors.

- [ ] **Step 8: Initial commit**

```powershell
git add requirements.txt config.py .env.example .gitignore ai sheets bot tests
git commit -m "feat: project scaffold with config and dependencies"
```

---

## Task 2: Google Sheets Client

**Files:**
- Create: `sheets/client.py`
- Create: `tests/test_sheets.py`
- Create: `tests/conftest.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/conftest.py`:
```python
import pytest

SAMPLE_RECORD = {
    "date": "2026-05-18",
    "amount": 45.50,
    "currency": "MYR",
    "merchant": "KFC",
    "category": "餐饮",
    "note": "",
    "source": "图片",
}
```

Create `tests/test_sheets.py`:
```python
from unittest.mock import MagicMock, patch, call
import pytest
from sheets.client import SheetsClient
from tests.conftest import SAMPLE_RECORD


@pytest.fixture
def mock_gc():
    with patch("sheets.client.gspread.service_account_from_dict") as mock_sa:
        mock_spreadsheet = MagicMock()
        mock_sa.return_value.open_by_key.return_value = mock_spreadsheet
        yield mock_sa, mock_spreadsheet


def make_client(mock_gc):
    mock_sa, mock_spreadsheet = mock_gc
    return SheetsClient(sheets_id="fake_id", service_account_info={"type": "service_account"}), mock_spreadsheet


def test_get_or_create_tab_creates_new_tab(mock_gc):
    client, mock_spreadsheet = make_client(mock_gc)
    mock_spreadsheet.worksheets.return_value = []
    mock_worksheet = MagicMock()
    mock_spreadsheet.add_worksheet.return_value = mock_worksheet

    ws = client._get_or_create_tab(12345)

    mock_spreadsheet.add_worksheet.assert_called_once_with(title="user_12345", rows=1000, cols=10)
    mock_worksheet.append_row.assert_called_once()  # headers written


def test_get_or_create_tab_returns_existing(mock_gc):
    client, mock_spreadsheet = make_client(mock_gc)
    mock_ws = MagicMock()
    mock_ws.title = "user_12345"
    mock_spreadsheet.worksheets.return_value = [mock_ws]

    ws = client._get_or_create_tab(12345)

    mock_spreadsheet.add_worksheet.assert_not_called()
    assert ws == mock_ws


def test_append_record(mock_gc):
    client, mock_spreadsheet = make_client(mock_gc)
    mock_ws = MagicMock()
    mock_ws.title = "user_12345"
    mock_spreadsheet.worksheets.return_value = [mock_ws]

    client.append_record(12345, SAMPLE_RECORD)

    mock_ws.append_row.assert_called_once_with(
        ["2026-05-18", 45.50, "MYR", "KFC", "餐饮", "", "图片"]
    )


def test_get_recent_records(mock_gc):
    client, mock_spreadsheet = make_client(mock_gc)
    mock_ws = MagicMock()
    mock_ws.title = "user_12345"
    # Row 1 = headers, rows 2-4 = data
    mock_ws.get_all_values.return_value = [
        ["日期", "金额", "货币", "商家", "类别", "备注", "来源"],
        ["2026-05-18", "45.50", "MYR", "KFC", "餐饮", "", "图片"],
        ["2026-05-17", "12.00", "MYR", "TNG", "交通", "", "语音"],
        ["2026-05-16", "8.50", "MYR", "7-11", "购物", "", "文字"],
    ]
    mock_spreadsheet.worksheets.return_value = [mock_ws]

    records = client.get_recent_records(12345, n=2)

    assert len(records) == 2
    assert records[0] == ["2026-05-17", "12.00", "MYR", "TNG", "交通", "", "语音"]
    assert records[1] == ["2026-05-18", "45.50", "MYR", "KFC", "餐饮", "", "图片"]


def test_delete_last_record(mock_gc):
    client, mock_spreadsheet = make_client(mock_gc)
    mock_ws = MagicMock()
    mock_ws.title = "user_12345"
    mock_ws.get_all_values.return_value = [
        ["日期", "金额", "货币", "商家", "类别", "备注", "来源"],
        ["2026-05-18", "45.50", "MYR", "KFC", "餐饮", "", "图片"],
    ]
    mock_spreadsheet.worksheets.return_value = [mock_ws]

    deleted = client.delete_last_record(12345)

    mock_ws.delete_rows.assert_called_once_with(2)
    assert deleted is True


def test_delete_last_record_empty_sheet(mock_gc):
    client, mock_spreadsheet = make_client(mock_gc)
    mock_ws = MagicMock()
    mock_ws.title = "user_12345"
    mock_ws.get_all_values.return_value = [
        ["日期", "金额", "货币", "商家", "类别", "备注", "来源"],
    ]
    mock_spreadsheet.worksheets.return_value = [mock_ws]

    deleted = client.delete_last_record(12345)

    mock_ws.delete_rows.assert_not_called()
    assert deleted is False


def test_get_monthly_summary(mock_gc):
    client, mock_spreadsheet = make_client(mock_gc)
    mock_ws = MagicMock()
    mock_ws.title = "user_12345"
    mock_ws.get_all_values.return_value = [
        ["日期", "金额", "货币", "商家", "类别", "备注", "来源"],
        ["2026-05-18", "45.50", "MYR", "KFC", "餐饮", "", "图片"],
        ["2026-05-17", "12.00", "MYR", "TNG", "交通", "", "语音"],
        ["2026-04-01", "100.00", "MYR", "Hotel", "住宿", "", "图片"],  # different month
    ]
    mock_spreadsheet.worksheets.return_value = [mock_ws]

    summary = client.get_monthly_summary(12345, year=2026, month=5)

    assert summary["total"] == pytest.approx(57.50)
    assert summary["by_category"]["餐饮"] == pytest.approx(45.50)
    assert summary["by_category"]["交通"] == pytest.approx(12.00)
    assert "住宿" not in summary["by_category"]
```

- [ ] **Step 2: Run tests to verify they fail**

```powershell
python -m pytest tests/test_sheets.py -v
```

Expected: `ImportError: No module named 'sheets.client'`

- [ ] **Step 3: Implement `sheets/client.py`**

```python
import gspread
from google.oauth2.service_account import Credentials
from config import SHEET_HEADERS


SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


class SheetsClient:
    def __init__(self, sheets_id: str, service_account_info: dict):
        self._sheets_id = sheets_id
        self._gc = gspread.service_account_from_dict(service_account_info)
        self._spreadsheet = self._gc.open_by_key(sheets_id)

    def _get_or_create_tab(self, telegram_id: int) -> gspread.Worksheet:
        tab_name = f"user_{telegram_id}"
        existing = {ws.title: ws for ws in self._spreadsheet.worksheets()}
        if tab_name in existing:
            return existing[tab_name]
        ws = self._spreadsheet.add_worksheet(title=tab_name, rows=1000, cols=10)
        ws.append_row(SHEET_HEADERS)
        return ws

    def append_record(self, telegram_id: int, record: dict) -> None:
        ws = self._get_or_create_tab(telegram_id)
        row = [
            record["date"],
            record["amount"],
            record["currency"],
            record["merchant"],
            record["category"],
            record.get("note", ""),
            record["source"],
        ]
        ws.append_row(row)

    def get_recent_records(self, telegram_id: int, n: int = 10) -> list[list]:
        ws = self._get_or_create_tab(telegram_id)
        all_rows = ws.get_all_values()
        data_rows = all_rows[1:]  # skip header
        return data_rows[-n:]

    def delete_last_record(self, telegram_id: int) -> bool:
        ws = self._get_or_create_tab(telegram_id)
        all_rows = ws.get_all_values()
        if len(all_rows) <= 1:  # only header or empty
            return False
        ws.delete_rows(len(all_rows))
        return True

    def get_monthly_summary(self, telegram_id: int, year: int, month: int) -> dict:
        ws = self._get_or_create_tab(telegram_id)
        all_rows = ws.get_all_values()
        data_rows = all_rows[1:]
        prefix = f"{year:04d}-{month:02d}"
        total = 0.0
        by_category: dict[str, float] = {}
        for row in data_rows:
            if not row[0].startswith(prefix):
                continue
            amount = float(row[1])
            category = row[4]
            total += amount
            by_category[category] = by_category.get(category, 0.0) + amount
        return {"total": total, "by_category": by_category}
```

- [ ] **Step 4: Run tests to verify they pass**

```powershell
python -m pytest tests/test_sheets.py -v
```

Expected: All 6 tests PASS.

- [ ] **Step 5: Commit**

```powershell
git add sheets/client.py tests/test_sheets.py tests/conftest.py
git commit -m "feat: Google Sheets client with tab-per-user isolation"
```

---

## Task 3: AI Vision — Receipt Photo Analysis

**Files:**
- Create: `ai/vision.py`
- Create: `tests/test_vision.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_vision.py`:
```python
from unittest.mock import MagicMock, patch
import pytest
from ai.vision import analyze_receipt


@pytest.fixture
def mock_gemini():
    with patch("ai.vision.genai.GenerativeModel") as mock_model_cls:
        mock_model = MagicMock()
        mock_model_cls.return_value = mock_model
        yield mock_model


def test_analyze_receipt_returns_expense_record(mock_gemini):
    mock_gemini.generate_content.return_value.text = '''
    {
        "date": "2026-05-18",
        "amount": 45.50,
        "currency": "MYR",
        "merchant": "KFC Sunway Pyramid",
        "category": "餐饮",
        "note": ""
    }
    '''
    result = analyze_receipt(b"fake_image_bytes")

    assert result["date"] == "2026-05-18"
    assert result["amount"] == 45.50
    assert result["currency"] == "MYR"
    assert result["merchant"] == "KFC Sunway Pyramid"
    assert result["category"] == "餐饮"
    assert result["source"] == "图片"


def test_analyze_receipt_handles_unreadable_image(mock_gemini):
    mock_gemini.generate_content.return_value.text = '{"error": "cannot read receipt"}'

    result = analyze_receipt(b"blurry_image")

    assert result is None


def test_analyze_receipt_handles_api_error(mock_gemini):
    mock_gemini.generate_content.side_effect = Exception("API timeout")

    result = analyze_receipt(b"any_bytes")

    assert result is None


def test_analyze_receipt_handles_malformed_json(mock_gemini):
    mock_gemini.generate_content.return_value.text = "Sorry, I cannot process this image."

    result = analyze_receipt(b"any_bytes")

    assert result is None
```

- [ ] **Step 2: Run tests to verify they fail**

```powershell
python -m pytest tests/test_vision.py -v
```

Expected: `ImportError: No module named 'ai.vision'`

- [ ] **Step 3: Implement `ai/vision.py`**

```python
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
        # Strip markdown code fences if present
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
```

- [ ] **Step 4: Run tests to verify they pass**

```powershell
python -m pytest tests/test_vision.py -v
```

Expected: All 4 tests PASS.

- [ ] **Step 5: Commit**

```powershell
git add ai/vision.py tests/test_vision.py
git commit -m "feat: Gemini Vision receipt analyzer"
```

---

## Task 4: AI Speech — Voice to Text

**Files:**
- Create: `ai/speech.py`
- Create: `tests/test_speech.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_speech.py`:
```python
from unittest.mock import MagicMock, patch
import pytest
from ai.speech import transcribe_voice


@pytest.fixture
def mock_groq():
    with patch("ai.speech.Groq") as mock_groq_cls:
        mock_client = MagicMock()
        mock_groq_cls.return_value = mock_client
        yield mock_client


def test_transcribe_voice_returns_text(mock_groq):
    mock_groq.audio.transcriptions.create.return_value = MagicMock(text="午饭KFC四十五块五毛")

    result = transcribe_voice(b"fake_ogg_bytes")

    assert result == "午饭KFC四十五块五毛"


def test_transcribe_voice_handles_api_error(mock_groq):
    mock_groq.audio.transcriptions.create.side_effect = Exception("API error")

    result = transcribe_voice(b"any_bytes")

    assert result is None


def test_transcribe_voice_returns_none_on_empty(mock_groq):
    mock_groq.audio.transcriptions.create.return_value = MagicMock(text="   ")

    result = transcribe_voice(b"silent_audio")

    assert result is None
```

- [ ] **Step 2: Run tests to verify they fail**

```powershell
python -m pytest tests/test_speech.py -v
```

Expected: `ImportError: No module named 'ai.speech'`

- [ ] **Step 3: Implement `ai/speech.py`**

```python
import io
from groq import Groq
from config import GROQ_API_KEY

_client = Groq(api_key=GROQ_API_KEY)


def transcribe_voice(audio_bytes: bytes) -> str | None:
    try:
        audio_file = io.BytesIO(audio_bytes)
        audio_file.name = "voice.ogg"
        response = _client.audio.transcriptions.create(
            file=audio_file,
            model="whisper-large-v3",
            language="zh",  # handles Chinese, English, Malay
        )
        text = response.text.strip()
        return text if text else None
    except Exception:
        return None
```

- [ ] **Step 4: Run tests to verify they pass**

```powershell
python -m pytest tests/test_speech.py -v
```

Expected: All 3 tests PASS.

- [ ] **Step 5: Commit**

```powershell
git add ai/speech.py tests/test_speech.py
git commit -m "feat: Groq Whisper voice transcription"
```

---

## Task 5: AI Parser — Natural Language Expense Extraction

**Files:**
- Create: `ai/parser.py`
- Create: `tests/test_parser.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_parser.py`:
```python
from unittest.mock import MagicMock, patch
import pytest
from ai.parser import parse_expense_text


@pytest.fixture
def mock_gemini():
    with patch("ai.parser.genai.GenerativeModel") as mock_model_cls:
        mock_model = MagicMock()
        mock_model_cls.return_value = mock_model
        yield mock_model


def test_parse_chinese_text(mock_gemini):
    mock_gemini.generate_content.return_value.text = '''
    {
        "date": "2026-05-18",
        "amount": 45.50,
        "currency": "MYR",
        "merchant": "KFC",
        "category": "餐饮",
        "note": ""
    }
    '''
    result = parse_expense_text("午饭KFC 45块5")

    assert result["amount"] == 45.50
    assert result["merchant"] == "KFC"
    assert result["category"] == "餐饮"


def test_parse_english_text(mock_gemini):
    mock_gemini.generate_content.return_value.text = '''
    {
        "date": "2026-05-18",
        "amount": 12.00,
        "currency": "MYR",
        "merchant": "Touch N Go",
        "category": "交通",
        "note": ""
    }
    '''
    result = parse_expense_text("Touch N Go reload 12")

    assert result["category"] == "交通"
    assert result["source"] == "文字"


def test_parse_returns_none_on_api_error(mock_gemini):
    mock_gemini.generate_content.side_effect = Exception("timeout")

    result = parse_expense_text("something")

    assert result is None


def test_parse_returns_none_on_malformed_response(mock_gemini):
    mock_gemini.generate_content.return_value.text = "I don't understand this expense."

    result = parse_expense_text("abcdef")

    assert result is None
```

- [ ] **Step 2: Run tests to verify they fail**

```powershell
python -m pytest tests/test_parser.py -v
```

Expected: `ImportError: No module named 'ai.parser'`

- [ ] **Step 3: Implement `ai/parser.py`**

```python
import json
from datetime import date
import google.generativeai as genai
from config import GOOGLE_GEMINI_API_KEY, EXPENSE_CATEGORIES

genai.configure(api_key=GOOGLE_GEMINI_API_KEY)

_PROMPT_TEMPLATE = f"""Extract expense information from this text message.
Today's date is {{today}}.

Return ONLY valid JSON with these exact keys:
- date: string in YYYY-MM-DD format
- amount: number
- currency: 3-char ISO code (default MYR if not mentioned)
- merchant: string (shop or payee name, or "Unknown" if not mentioned)
- category: one of {EXPENSE_CATEGORIES}
- note: string (empty string if nothing to add)

If you cannot extract a valid expense from the text, return: {{"error": "cannot parse"}}
Text: {{text}}"""


def parse_expense_text(text: str) -> dict | None:
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        prompt = _PROMPT_TEMPLATE.format(today=date.today().isoformat(), text=text)
        response = model.generate_content(prompt)
        raw = response.text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        data = json.loads(raw)
        if "error" in data:
            return None
        data["source"] = "文字"
        return data
    except Exception:
        return None
```

- [ ] **Step 4: Run tests to verify they pass**

```powershell
python -m pytest tests/test_parser.py -v
```

Expected: All 4 tests PASS.

- [ ] **Step 5: Commit**

```powershell
git add ai/parser.py tests/test_parser.py
git commit -m "feat: Gemini natural language expense parser"
```

---

## Task 6: Bot Keyboards

**Files:**
- Create: `bot/keyboards.py`

No tests needed — keyboard builders return static Telegram objects with no logic to test.

- [ ] **Step 1: Implement `bot/keyboards.py`**

```python
from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def record_confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🗑️ 删除这条", callback_data="delete_last"),
        ]
    ])
```

- [ ] **Step 2: Commit**

```powershell
git add bot/keyboards.py
git commit -m "feat: inline keyboard builders"
```

---

## Task 7: Bot Commands (`/start`, `/summary`, `/list`, `/delete`)

**Files:**
- Create: `bot/commands.py`

- [ ] **Step 1: Implement `bot/commands.py`**

```python
from datetime import date
from telegram import Update
from telegram.ext import ContextTypes
from sheets.client import SheetsClient
import config


def _make_client() -> SheetsClient:
    return SheetsClient(
        sheets_id=config.GOOGLE_SHEETS_ID,
        service_account_info=config.GOOGLE_SERVICE_ACCOUNT_JSON,
    )


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "👋 *记账机器人* 已就绪！\n\n"
        "📷 *拍照记账* — 发送收据图片\n"
        "🎙️ *语音记账* — 发语音消息（例：\"午饭麦当劳25块\"）\n"
        "📝 *文字记账* — 直接发文字（例：\"KFC 45.50\"）\n\n"
        "📋 *命令：*\n"
        "/summary — 本月汇总\n"
        "/list — 最近10条记录\n"
        "/delete — 删除最后一条"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def cmd_summary(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    client = _make_client()
    today = date.today()
    summary = client.get_monthly_summary(user_id, year=today.year, month=today.month)

    if summary["total"] == 0:
        await update.message.reply_text("📊 本月暂无记录。")
        return

    lines = [f"📊 *{today.year}年{today.month}月账单汇总*\n"]
    for cat, amt in sorted(summary["by_category"].items(), key=lambda x: -x[1]):
        lines.append(f"  {cat}：{amt:.2f} MYR")
    lines.append(f"\n💰 *总计：{summary['total']:.2f} MYR*")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def cmd_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    client = _make_client()
    records = client.get_recent_records(user_id, n=10)

    if not records:
        await update.message.reply_text("📋 暂无记录。")
        return

    lines = ["📋 *最近记录：*\n"]
    for row in reversed(records):
        lines.append(f"  {row[0]}  {row[3]}  {float(row[1]):.2f} {row[2]}  [{row[4]}]")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def cmd_delete(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    client = _make_client()
    deleted = client.delete_last_record(user_id)
    if deleted:
        await update.message.reply_text("🗑️ 最后一条记录已删除。")
    else:
        await update.message.reply_text("没有可删除的记录。")
```

- [ ] **Step 2: Commit**

```powershell
git add bot/commands.py
git commit -m "feat: bot commands /start /summary /list /delete"
```

---

## Task 8: Bot Message Handlers (Photo, Voice, Text)

**Files:**
- Create: `bot/handlers.py`

- [ ] **Step 1: Implement `bot/handlers.py`**

```python
import io
from datetime import date
from telegram import Update
from telegram.ext import ContextTypes
from ai.vision import analyze_receipt
from ai.speech import transcribe_voice
from ai.parser import parse_expense_text
from sheets.client import SheetsClient
from bot.keyboards import record_confirm_keyboard
import config


def _make_client() -> SheetsClient:
    return SheetsClient(
        sheets_id=config.GOOGLE_SHEETS_ID,
        service_account_info=config.GOOGLE_SERVICE_ACCOUNT_JSON,
    )


def _format_record(record: dict) -> str:
    return (
        f"✅ *已记录！*\n\n"
        f"📅 日期：{record['date']}\n"
        f"💰 金额：{record['amount']:.2f} {record['currency']}\n"
        f"🏪 商家：{record['merchant']}\n"
        f"🏷️ 类别：{record['category']}\n"
        f"📝 备注：{record.get('note') or '—'}"
    )


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("🔍 正在分析收据...")
    photo = update.message.photo[-1]  # highest resolution
    file = await context.bot.get_file(photo.file_id)
    buf = io.BytesIO()
    await file.download_to_memory(buf)
    image_bytes = buf.getvalue()

    record = analyze_receipt(image_bytes)
    if record is None:
        await update.message.reply_text(
            "❌ 无法识别这张图片，请确保图片清晰，并重新发送。"
        )
        return

    if not record.get("date"):
        record["date"] = date.today().isoformat()

    _make_client().append_record(update.effective_user.id, record)
    await update.message.reply_text(
        _format_record(record),
        parse_mode="Markdown",
        reply_markup=record_confirm_keyboard(),
    )


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("🎙️ 正在识别语音...")
    voice = update.message.voice
    file = await context.bot.get_file(voice.file_id)
    buf = io.BytesIO()
    await file.download_to_memory(buf)
    audio_bytes = buf.getvalue()

    text = transcribe_voice(audio_bytes)
    if text is None:
        await update.message.reply_text("❌ 语音识别失败，请重试。")
        return

    record = parse_expense_text(text)
    if record is None:
        await update.message.reply_text(
            f'🔤 识别到文字："{text}"\n\n❌ 无法提取账单信息，请尝试说清楚金额和商家。'
        )
        return

    record["source"] = "语音"
    if not record.get("date"):
        record["date"] = date.today().isoformat()

    _make_client().append_record(update.effective_user.id, record)
    await update.message.reply_text(
        _format_record(record),
        parse_mode="Markdown",
        reply_markup=record_confirm_keyboard(),
    )


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text
    if text.startswith("/"):
        return  # commands handled separately

    record = parse_expense_text(text)
    if record is None:
        await update.message.reply_text(
            "❓ 没有识别到账单信息。\n\n试试这样发：\"KFC 45.50\" 或 \"午饭 麦当劳 25\""
        )
        return

    if not record.get("date"):
        record["date"] = date.today().isoformat()

    _make_client().append_record(update.effective_user.id, record)
    await update.message.reply_text(
        _format_record(record),
        parse_mode="Markdown",
        reply_markup=record_confirm_keyboard(),
    )


async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if query.data == "delete_last":
        deleted = _make_client().delete_last_record(query.from_user.id)
        if deleted:
            await query.edit_message_text("🗑️ 已删除最后一条记录。")
        else:
            await query.edit_message_text("没有可删除的记录。")
```

- [ ] **Step 2: Commit**

```powershell
git add bot/handlers.py
git commit -m "feat: bot message handlers for photo, voice, and text"
```

---

## Task 9: Main Entry Point

**Files:**
- Create: `main.py`

- [ ] **Step 1: Implement `main.py`**

```python
import logging
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)
import config
from bot.commands import cmd_start, cmd_summary, cmd_list, cmd_delete
from bot.handlers import handle_photo, handle_voice, handle_text, handle_callback_query

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)


def main() -> None:
    app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("summary", cmd_summary))
    app.add_handler(CommandHandler("list", cmd_list))
    app.add_handler(CommandHandler("delete", cmd_delete))

    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(CallbackQueryHandler(handle_callback_query))

    logging.info("Bot started — polling for messages...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Commit**

```powershell
git add main.py
git commit -m "feat: main entry point with all handlers registered"
```

---

## Task 10: Deployment Config

**Files:**
- Create: `Procfile`

- [ ] **Step 1: Create `Procfile`**

```
worker: python main.py
```

- [ ] **Step 2: Commit**

```powershell
git add Procfile
git commit -m "chore: add Render deployment Procfile"
```

---

## Task 11: Local End-to-End Test

- [ ] **Step 1: Run all unit tests**

```powershell
python -m pytest tests/ -v
```

Expected: All tests PASS. No warnings about missing modules.

- [ ] **Step 2: Copy `.env.example` to `.env` and fill in your API keys**

```powershell
copy .env.example .env
```

Open `.env` in a text editor and fill in:
- `TELEGRAM_BOT_TOKEN` — from BotFather
- `GOOGLE_GEMINI_API_KEY` — from Google AI Studio
- `GROQ_API_KEY` — from Groq Console
- `GOOGLE_SHEETS_ID` — from your Google Sheet URL
- `GOOGLE_SERVICE_ACCOUNT_JSON` — paste the entire contents of your service account JSON file as a single line (no newlines)

> **Tip for GOOGLE_SERVICE_ACCOUNT_JSON:** Open the JSON file, select all, copy, then paste as one line. It starts with `{"type":"service_account",...}`.

- [ ] **Step 3: Start the bot locally**

```powershell
python main.py
```

Expected output:
```
INFO - Application started
INFO - Bot started — polling for messages...
```

- [ ] **Step 4: Test in Telegram (checklist)**

Open your bot in Telegram and run each test:

| # | Action | Expected Bot Response |
|---|--------|-----------------------|
| 1 | Send `/start` | Welcome message with instructions |
| 2 | Send a clear receipt photo | "✅ 已记录！" with extracted details |
| 3 | Check Google Sheet | New row added in your tab `user_<your_id>` |
| 4 | Send voice: "午饭KFC四十五块五" | "✅ 已记录！" with KFC, 45.50 |
| 5 | Send text: "Grab 12.50" | "✅ 已记录！" with 交通 category |
| 6 | Send `/list` | Last 3 records shown |
| 7 | Send `/summary` | Current month total and breakdown |
| 8 | Send `/delete` | Last record deleted |
| 9 | Check Google Sheet again | Confirm deletion |

- [ ] **Step 5: Multi-user test**

Ask a friend to message your bot (or use a second Telegram account). After they send a receipt photo:
- Their records should appear in a NEW tab in the Google Sheet named `user_<their_id>`
- Your records in `user_<your_id>` should be unaffected.

---

## Task 12: Deploy to Render

- [ ] **Step 1: Push to GitHub**

Create a new GitHub repo (e.g., `telegram-accounting-bot`) and push:
```powershell
git remote add origin https://github.com/YOUR_USERNAME/telegram-accounting-bot.git
git push -u origin main
```

- [ ] **Step 2: Create a Render Web Service**

1. Go to [https://render.com](https://render.com) and log in
2. Click **「New」** → **「Web Service」**
3. Connect your GitHub repo
4. Set the following:
   - **Environment:** `Python`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python main.py`
   - **Instance Type:** Free

- [ ] **Step 3: Add environment variables in Render**

In the Render dashboard → your service → **「Environment」** tab, add all 5 variables from `.env.example` with your real values.

> **Important:** For `GOOGLE_SERVICE_ACCOUNT_JSON`, paste the entire JSON on one line.

- [ ] **Step 4: Deploy and verify**

1. Click **「Deploy」**
2. Watch the logs — look for `Bot started — polling for messages...`
3. Send `/start` to your bot from your phone
4. Confirm it responds within 5 seconds

---

## Self-Review Summary

- ✅ All spec requirements covered: photo, voice, text input, Google Sheets storage, multi-user isolation, `/start` `/summary` `/list` `/delete` commands
- ✅ No TBDs or placeholders — all code is complete
- ✅ Type signatures consistent: `analyze_receipt → dict | None`, `transcribe_voice → str | None`, `parse_expense_text → dict | None`, all feed into `SheetsClient.append_record(telegram_id, record)`
- ✅ `ExpenseRecord` dict structure defined once in file map and used consistently throughout
- ✅ Tests mock external APIs — no real API calls in test suite
- ✅ `source` field set correctly: "图片" in vision.py, "语音" in handlers.py for voice, "文字" in parser.py
