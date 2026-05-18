import io
from groq import Groq
from config import GROQ_API_KEY

_client = None


def _get_client():
    global _client
    if _client is None:
        _client = Groq(api_key=GROQ_API_KEY)
    return _client


def transcribe_voice(audio_bytes: bytes) -> str | None:
    try:
        audio_file = io.BytesIO(audio_bytes)
        audio_file.name = "voice.ogg"
        response = _get_client().audio.transcriptions.create(
            file=audio_file,
            model="whisper-large-v3",
            language="zh",
        )
        text = response.text.strip()
        return text if text else None
    except Exception:
        return None
