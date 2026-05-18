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
