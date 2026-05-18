import logging
import warnings
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

try:
    import truststore
    truststore.inject_into_ssl()
except Exception:
    pass  # truststore optional — fall back to verify=False below

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)
from telegram.request import HTTPXRequest
import config
from bot.commands import cmd_start, cmd_summary, cmd_list, cmd_delete
from bot.handlers import handle_photo, handle_voice, handle_text, handle_callback_query

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)


def main() -> None:
    # Build custom HTTPXRequest with SSL verification disabled.
    # Required on machines with intercepting proxies that inject certificates
    # not trusted by the default CA bundle.
    _request = HTTPXRequest(httpx_kwargs={"verify": False})
    _get_updates_request = HTTPXRequest(httpx_kwargs={"verify": False})

    app = (
        Application.builder()
        .token(config.TELEGRAM_BOT_TOKEN)
        .request(_request)
        .get_updates_request(_get_updates_request)
        .build()
    )

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
