---
name: run-and-test-locally
description: Use when setting up the local dev environment, running the bot locally, running the test suite, or debugging bot responses without deploying to Render.
---

# Run and Test Locally

## Quick Start (First Time)

```powershell
cd C:\cld.dev\telegram-accounting-bot

# 1. Create venv and install dev dependencies
python -m venv venv
venv\Scripts\activate
pip install -r requirements-dev.txt

# 2. Copy env template and fill in your API keys
copy .env.example .env
# Open .env in editor and fill in all 5 values

# 3. Run the bot
python main.py
```

Expected output: `INFO - Bot started — polling for messages...`

## Run Tests (No API Keys Needed)

Tests mock all external APIs. Use dummy values:

```powershell
$env:TELEGRAM_BOT_TOKEN="dummy"
$env:GOOGLE_GEMINI_API_KEY="dummy"
$env:GROQ_API_KEY="dummy"
$env:GOOGLE_SHEETS_ID="dummy"
$env:GOOGLE_SERVICE_ACCOUNT_JSON='{"type":"service_account"}'

venv\Scripts\python -m pytest tests/ -v
```

Expected: **18 passed** (7 sheets + 4 vision + 3 speech + 4 parser)

Run a single test file:
```powershell
venv\Scripts\python -m pytest tests/test_vision.py -v
```

## Required .env Values

| Variable | Where to Get |
|----------|-------------|
| `TELEGRAM_BOT_TOKEN` | @BotFather on Telegram → `/newbot` |
| `GOOGLE_GEMINI_API_KEY` | [aistudio.google.com](https://aistudio.google.com) → Get API key |
| `GROQ_API_KEY` | [console.groq.com](https://console.groq.com) → API Keys |
| `GOOGLE_SHEETS_ID` | Google Sheet URL: `.../spreadsheets/d/**THIS_PART**/edit` |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | Contents of downloaded service account JSON, all on one line |

## GOOGLE_SERVICE_ACCOUNT_JSON Format

Paste the entire JSON file contents as a single line — no newlines:
```
GOOGLE_SERVICE_ACCOUNT_JSON={"type":"service_account","project_id":"...","private_key":"-----BEGIN RSA...","client_email":"...@....iam.gserviceaccount.com",...}
```

## Debugging Common Issues

| Problem | Fix |
|---------|-----|
| `KeyError: 'TELEGRAM_BOT_TOKEN'` | `.env` file missing or not in project root |
| `ValueError: GOOGLE_SERVICE_ACCOUNT_JSON must be valid JSON` | JSON has newlines — paste as one line |
| `gspread.exceptions.SpreadsheetNotFound` | Wrong Sheet ID, or service account not shared on the Sheet |
| Bot doesn't respond to messages | Check `python main.py` is running; check BotFather token |
| Tests fail with `ImportError` | Run `pip install -r requirements-dev.txt` in venv |

## Testing a Specific Feature Manually

After `python main.py` is running, open Telegram and test:

| Feature | Test |
|---------|------|
| Bot alive | Send `/start` |
| Photo recognition | Send a clear receipt photo |
| Voice recording | Record: "午饭麦当劳二十五块" |
| Text input | Send: `KFC 45.50` |
| Monthly summary | Send `/summary` |
| Recent records | Send `/list` |
| Delete last | Send `/delete` |

Check Google Sheet after each to confirm data was written to `user_{your_telegram_id}` tab.
