from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def record_confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🗑️ 删除这条", callback_data="delete_last"),
        ]
    ])
