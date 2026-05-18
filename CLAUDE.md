# Telegram AI Accounting Bot — Claude Guide

## What This Project Does

A Telegram bot that lets users record expenses by sending receipt photos, voice messages, or text. AI extracts expense info (amount, date, merchant, category) and writes it to Google Sheets. Fully free-tier: Gemini Vision + Groq Whisper + Google Sheets.

## Architecture

```
Telegram message
  ├── 📷 Photo  → ai/vision.py   (Gemini Vision)  → ExpenseRecord
  ├── 🎙️ Voice  → ai/speech.py  (Groq Whisper)   → text
  │              → ai/parser.py  (Gemini text)    → ExpenseRecord
  └── 📝 Text   → ai/parser.py  (Gemini text)    → ExpenseRecord
                                                        ↓
                                               sheets/client.py
                                               (per-user Sheet tab)
```

## Key Files

| File | Purpose |
|------|---------|
| `config.py` | All env vars + `EXPENSE_CATEGORIES` + `SHEET_HEADERS` |
| `ai/vision.py` | `analyze_receipt(bytes) → dict\|None` |
| `ai/speech.py` | `transcribe_voice(bytes) → str\|None` |
| `ai/parser.py` | `parse_expense_text(str) → dict\|None` |
| `sheets/client.py` | `SheetsClient` — append, list, delete, summary |
| `bot/handlers.py` | Photo/voice/text/callback message handlers |
| `bot/commands.py` | `/start` `/summary` `/list` `/delete` |
| `bot/keyboards.py` | Inline keyboards |
| `main.py` | Bot startup + handler registration |

## ExpenseRecord Shape

```python
{
    "date": "2026-05-18",   # YYYY-MM-DD
    "amount": 45.50,        # float
    "currency": "MYR",      # 3-char ISO
    "merchant": "KFC",      # str
    "category": "餐饮",      # see EXPENSE_CATEGORIES in config.py
    "note": "",             # str, may be empty
    "source": "图片"         # 图片 | 语音 | 文字
}
```

## Expense Categories

```python
["餐饮", "购物", "交通", "娱乐", "医疗", "住宿", "水电", "其他"]
```

## Available Skills

Project skills live in `.claude/skills/`. Use them by invoking:

| Skill | When to Use |
|-------|------------|
| `add-bot-command` | Adding a new `/command` to the bot |
| `extend-ai-module` | Adding/swapping an AI provider or module |
| `run-and-test-locally` | Setting up local dev, running tests |
| `deploy-to-render` | Deploying or updating on Render.com |

## Testing

```powershell
# Set dummy env vars then run
$env:TELEGRAM_BOT_TOKEN="dummy"; $env:GOOGLE_GEMINI_API_KEY="dummy"
$env:GROQ_API_KEY="dummy"; $env:GOOGLE_SHEETS_ID="dummy"
$env:GOOGLE_SERVICE_ACCOUNT_JSON='{"type":"service_account"}'
venv\Scripts\python -m pytest tests/ -v
```

Tests mock all external APIs — no real API calls needed.

## Environment Variables

```
TELEGRAM_BOT_TOKEN          # From @BotFather
GOOGLE_GEMINI_API_KEY       # From aistudio.google.com
GROQ_API_KEY                # From console.groq.com
GOOGLE_SHEETS_ID            # From Google Sheets URL
GOOGLE_SERVICE_ACCOUNT_JSON # Full service account JSON, single line
```

## Multi-User Design

Each Telegram user (`telegram_id`) gets their own Sheet tab named `user_{id}`. `SheetsClient._get_or_create_tab(telegram_id)` handles creation automatically.
