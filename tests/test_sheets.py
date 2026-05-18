from unittest.mock import MagicMock, patch, call
import pytest
from sheets.client import SheetsClient
from tests.conftest import SAMPLE_RECORD


@pytest.fixture
def mock_gc():
    with patch("sheets.client.gspread.service_account_from_dict") as mock_sa:
        mock_spreadsheet = MagicMock()
        mock_sa.return_value.open_by_key.return_value = mock_spreadsheet
        yield mock_sa, mock_spreadsheet


def make_client(mock_gc):
    mock_sa, mock_spreadsheet = mock_gc
    return SheetsClient(sheets_id="fake_id", service_account_info={"type": "service_account"}), mock_spreadsheet


def test_get_or_create_tab_creates_new_tab(mock_gc):
    client, mock_spreadsheet = make_client(mock_gc)
    mock_spreadsheet.worksheets.return_value = []
    mock_worksheet = MagicMock()
    mock_spreadsheet.add_worksheet.return_value = mock_worksheet

    ws = client._get_or_create_tab(12345)

    mock_spreadsheet.add_worksheet.assert_called_once_with(title="user_12345", rows=1000, cols=10)
    mock_worksheet.append_row.assert_called_once()  # headers written


def test_get_or_create_tab_returns_existing(mock_gc):
    client, mock_spreadsheet = make_client(mock_gc)
    mock_ws = MagicMock()
    mock_ws.title = "user_12345"
    mock_spreadsheet.worksheets.return_value = [mock_ws]

    ws = client._get_or_create_tab(12345)

    mock_spreadsheet.add_worksheet.assert_not_called()
    assert ws == mock_ws


def test_append_record(mock_gc):
    client, mock_spreadsheet = make_client(mock_gc)
    mock_ws = MagicMock()
    mock_ws.title = "user_12345"
    mock_spreadsheet.worksheets.return_value = [mock_ws]

    client.append_record(12345, SAMPLE_RECORD)

    mock_ws.append_row.assert_called_once_with(
        ["2026-05-18", 45.50, "MYR", "KFC", "餐饮", "", "图片"]
    )


def test_get_recent_records(mock_gc):
    client, mock_spreadsheet = make_client(mock_gc)
    mock_ws = MagicMock()
    mock_ws.title = "user_12345"
    mock_ws.get_all_values.return_value = [
        ["日期", "金额", "货币", "商家", "类别", "备注", "来源"],
        ["2026-05-18", "45.50", "MYR", "KFC", "餐饮", "", "图片"],
        ["2026-05-17", "12.00", "MYR", "TNG", "交通", "", "语音"],
        ["2026-05-16", "8.50", "MYR", "7-11", "购物", "", "文字"],
    ]
    mock_spreadsheet.worksheets.return_value = [mock_ws]

    records = client.get_recent_records(12345, n=2)

    assert len(records) == 2
    assert records[0] == ["2026-05-17", "12.00", "MYR", "TNG", "交通", "", "语音"]
    assert records[1] == ["2026-05-18", "45.50", "MYR", "KFC", "餐饮", "", "图片"]


def test_delete_last_record(mock_gc):
    client, mock_spreadsheet = make_client(mock_gc)
    mock_ws = MagicMock()
    mock_ws.title = "user_12345"
    mock_ws.get_all_values.return_value = [
        ["日期", "金额", "货币", "商家", "类别", "备注", "来源"],
        ["2026-05-18", "45.50", "MYR", "KFC", "餐饮", "", "图片"],
    ]
    mock_spreadsheet.worksheets.return_value = [mock_ws]

    deleted = client.delete_last_record(12345)

    mock_ws.delete_rows.assert_called_once_with(2)
    assert deleted is True


def test_delete_last_record_empty_sheet(mock_gc):
    client, mock_spreadsheet = make_client(mock_gc)
    mock_ws = MagicMock()
    mock_ws.title = "user_12345"
    mock_ws.get_all_values.return_value = [
        ["日期", "金额", "货币", "商家", "类别", "备注", "来源"],
    ]
    mock_spreadsheet.worksheets.return_value = [mock_ws]

    deleted = client.delete_last_record(12345)

    mock_ws.delete_rows.assert_not_called()
    assert deleted is False


def test_get_monthly_summary(mock_gc):
    client, mock_spreadsheet = make_client(mock_gc)
    mock_ws = MagicMock()
    mock_ws.title = "user_12345"
    mock_ws.get_all_values.return_value = [
        ["日期", "金额", "货币", "商家", "类别", "备注", "来源"],
        ["2026-05-18", "45.50", "MYR", "KFC", "餐饮", "", "图片"],
        ["2026-05-17", "12.00", "MYR", "TNG", "交通", "", "语音"],
        ["2026-04-01", "100.00", "MYR", "Hotel", "住宿", "", "图片"],
    ]
    mock_spreadsheet.worksheets.return_value = [mock_ws]

    summary = client.get_monthly_summary(12345, year=2026, month=5)

    assert summary["total"] == pytest.approx(57.50)
    assert summary["by_category"]["餐饮"] == pytest.approx(45.50)
    assert summary["by_category"]["交通"] == pytest.approx(12.00)
    assert "住宿" not in summary["by_category"]
