from unittest.mock import MagicMock, patch
import pytest
from ai.parser import parse_expense_text


@pytest.fixture
def mock_gemini():
    with patch("ai.parser.genai.GenerativeModel") as mock_model_cls:
        mock_model = MagicMock()
        mock_model_cls.return_value = mock_model
        yield mock_model


def test_parse_chinese_text(mock_gemini):
    mock_gemini.generate_content.return_value.text = '''
    {
        "date": "2026-05-18",
        "amount": 45.50,
        "currency": "MYR",
        "merchant": "KFC",
        "category": "餐饮",
        "note": ""
    }
    '''
    result = parse_expense_text("午饭KFC 45块5")

    assert result["amount"] == 45.50
    assert result["merchant"] == "KFC"
    assert result["category"] == "餐饮"


def test_parse_english_text(mock_gemini):
    mock_gemini.generate_content.return_value.text = '''
    {
        "date": "2026-05-18",
        "amount": 12.00,
        "currency": "MYR",
        "merchant": "Touch N Go",
        "category": "交通",
        "note": ""
    }
    '''
    result = parse_expense_text("Touch N Go reload 12")

    assert result["category"] == "交通"
    assert result["source"] == "文字"


def test_parse_returns_none_on_api_error(mock_gemini):
    mock_gemini.generate_content.side_effect = Exception("timeout")

    result = parse_expense_text("something")

    assert result is None


def test_parse_returns_none_on_malformed_response(mock_gemini):
    mock_gemini.generate_content.return_value.text = "I don't understand this expense."

    result = parse_expense_text("abcdef")

    assert result is None
