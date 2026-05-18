---
name: add-bot-command
description: Use when adding a new slash command (e.g. /export, /clear, /stats) to the Telegram accounting bot. Covers the two-file pattern, handler signature, SheetsClient usage, and registration in main.py.
---

# Add Bot Command

## Overview

Every `/command` requires changes to exactly **2 files**: `bot/commands.py` (the handler function) and `main.py` (the registration). Nothing else.

## Quick Reference

| Step | File | What to do |
|------|------|-----------|
| 1 | `bot/commands.py` | Add `async def cmd_{name}(update, context)` |
| 2 | `main.py` | Add `app.add_handler(CommandHandler("{name}", cmd_{name}))` |

## Step 1 — Write the Handler (`bot/commands.py`)

```python
async def cmd_export(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    client = _make_client()           # creates SheetsClient — already defined in this file
    today = date.today()

    # use SheetsClient methods:
    # client.get_recent_records(user_id, n=10)      → list[list[str]]
    # client.get_monthly_summary(user_id, year, month) → {"total": float, "by_category": dict}
    # client.append_record(user_id, record)
    # client.delete_last_record(user_id)             → bool

    await update.message.reply_text("Your reply here", parse_mode="Markdown")
```

**Rules:**
- Function name must be `cmd_{command_name}` (matches Telegram command)
- First two params always `update: Update, context: ContextTypes.DEFAULT_TYPE`
- Always `async def` — this is an async bot
- Get user id with `update.effective_user.id`
- Use `_make_client()` (already in file) — don't import SheetsClient directly

## Step 2 — Register in `main.py`

Add inside `main()`, with the other `CommandHandler` lines:

```python
app.add_handler(CommandHandler("export", cmd_export))
```

Also add the import at the top of `main.py`:

```python
from bot.commands import cmd_start, cmd_summary, cmd_list, cmd_delete, cmd_export
```

## Sending Formatted Replies

```python
# Plain text
await update.message.reply_text("Done!")

# Markdown (bold, italic, code)
await update.message.reply_text("*Bold* and `code`", parse_mode="Markdown")

# With inline keyboard
from bot.keyboards import record_confirm_keyboard
await update.message.reply_text("text", reply_markup=record_confirm_keyboard())
```

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Forgetting `async def` | All handlers must be async |
| Using `update.message.from_user.id` | Use `update.effective_user.id` instead |
| Importing SheetsClient directly | Use `_make_client()` already defined in commands.py |
| Forgetting to register in `main.py` | Command exists but bot won't respond to it |
| Forgetting to add import in `main.py` | `ImportError` at startup |
