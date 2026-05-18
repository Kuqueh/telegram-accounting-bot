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
