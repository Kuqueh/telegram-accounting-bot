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
    photo = update.message.photo[-1]
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
        return

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
