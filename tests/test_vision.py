from unittest.mock import MagicMock, patch
import pytest
from ai.vision import analyze_receipt


@pytest.fixture
def mock_gemini():
    with patch("ai.vision.genai.GenerativeModel") as mock_model_cls:
        mock_model = MagicMock()
        mock_model_cls.return_value = mock_model
        yield mock_model


def test_analyze_receipt_returns_expense_record(mock_gemini):
    mock_gemini.generate_content.return_value.text = '''
    {
        "date": "2026-05-18",
        "amount": 45.50,
        "currency": "MYR",
        "merchant": "KFC Sunway Pyramid",
        "category": "餐饮",
        "note": ""
    }
    '''
    result = analyze_receipt(b"fake_image_bytes")

    assert result["date"] == "2026-05-18"
    assert result["amount"] == 45.50
    assert result["currency"] == "MYR"
    assert result["merchant"] == "KFC Sunway Pyramid"
    assert result["category"] == "餐饮"
    assert result["source"] == "图片"


def test_analyze_receipt_handles_unreadable_image(mock_gemini):
    mock_gemini.generate_content.return_value.text = '{"error": "cannot read receipt"}'

    result = analyze_receipt(b"blurry_image")

    assert result is None


def test_analyze_receipt_handles_api_error(mock_gemini):
    mock_gemini.generate_content.side_effect = Exception("API timeout")

    result = analyze_receipt(b"any_bytes")

    assert result is None


def test_analyze_receipt_handles_malformed_json(mock_gemini):
    mock_gemini.generate_content.return_value.text = "Sorry, I cannot process this image."

    result = analyze_receipt(b"any_bytes")

    assert result is None
