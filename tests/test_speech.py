from unittest.mock import MagicMock, patch
import pytest
from ai.speech import transcribe_voice


@pytest.fixture
def mock_groq():
    with patch("ai.speech.Groq") as mock_groq_cls, \
         patch("ai.speech._client", None):
        mock_client = MagicMock()
        mock_groq_cls.return_value = mock_client
        yield mock_client


def test_transcribe_voice_returns_text(mock_groq):
    mock_groq.audio.transcriptions.create.return_value = MagicMock(text="午饭KFC四十五块五毛")

    result = transcribe_voice(b"fake_ogg_bytes")

    assert result == "午饭KFC四十五块五毛"


def test_transcribe_voice_handles_api_error(mock_groq):
    mock_groq.audio.transcriptions.create.side_effect = Exception("API error")

    result = transcribe_voice(b"any_bytes")

    assert result is None


def test_transcribe_voice_returns_none_on_empty(mock_groq):
    mock_groq.audio.transcriptions.create.return_value = MagicMock(text="   ")

    result = transcribe_voice(b"silent_audio")

    assert result is None
