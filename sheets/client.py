import gspread
from config import SHEET_HEADERS


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
        sorted_rows = sorted(data_rows, key=lambda r: r[0])
        return sorted_rows[-n:]

    def delete_last_record(self, telegram_id: int) -> bool:
        ws = self._get_or_create_tab(telegram_id)
        all_rows = ws.get_all_values()
        if len(all_rows) <= 1:
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
