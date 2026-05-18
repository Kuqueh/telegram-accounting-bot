---
name: deploy-to-render
description: Use when deploying the bot to Render.com for the first time, pushing a code update to production, checking deploy logs, or troubleshooting a bot that works locally but not on Render.
---

# Deploy to Render

## First Deploy

### 1. Push code to GitHub
```powershell
git -C "C:\cld.dev\telegram-accounting-bot" push origin main
```

### 2. Create Render service
1. Go to [render.com](https://render.com) → **New** → **Web Service**
2. Connect your GitHub repo: `Kuqueh/telegram-accounting-bot`
3. Set build & start:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python main.py`
   - **Instance Type:** Free

### 3. Add environment variables
In Render dashboard → your service → **Environment** tab, add all 5 vars:

| Key | Value |
|-----|-------|
| `TELEGRAM_BOT_TOKEN` | Your BotFather token |
| `GOOGLE_GEMINI_API_KEY` | Your Gemini key |
| `GROQ_API_KEY` | Your Groq key |
| `GOOGLE_SHEETS_ID` | Your Sheet document ID |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | Full JSON contents, **one line, no newlines** |

### 4. Deploy and verify
- Click **Deploy** → watch logs → look for `Bot started — polling for messages...`
- Open Telegram → send `/start` → bot should reply within 5 seconds

## Pushing an Update

```powershell
cd C:\cld.dev\telegram-accounting-bot
git add -A
git commit -m "feat: describe your change"
git push origin main
```

Render auto-deploys on every push to `main`. Watch the deploy logs in the Render dashboard.

## Render Free Tier Notes

| Limit | Value |
|-------|-------|
| Hours/month | 750 hrs (enough for ~1 service running 24/7) |
| Sleep after inactivity | Yes — but long-polling bots don't sleep (they keep polling) |
| Cold start | ~30 sec if service does sleep |

**Keep alive tip:** The bot uses `run_polling()` which keeps a persistent connection — Render won't sleep it as long as the process is running.

## Reading Logs

In Render dashboard → your service → **Logs** tab. Look for:
- ✅ `Bot started — polling for messages...` — running correctly
- ❌ `KeyError: 'TELEGRAM_BOT_TOKEN'` — env var missing
- ❌ `ValueError: GOOGLE_SERVICE_ACCOUNT_JSON must be valid JSON` — JSON has newlines
- ❌ `Conflict: terminated by other getUpdates request` — another instance is running (stop it)

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Bot works locally but not on Render | Check all 5 env vars are set in Render dashboard |
| Deploy succeeds but bot doesn't respond | Check logs for startup error |
| `Conflict: terminated by other getUpdates` | Stop local `python main.py` before deploying — only one polling instance allowed |
| Service keeps restarting | Check logs for Python exception at startup |
| `GOOGLE_SERVICE_ACCOUNT_JSON` error | Re-paste JSON as one single line with no line breaks |
