import io
import logging

import httpx
from groq import Groq
from config import GROQ_API_KEY

logger = logging.getLogger(__name__)

_client = None


def _get_client():
    global _client
    if _client is None:
        # Pass a custom httpx client with SSL verification disabled.
        # Required on machines with intercepting proxies that inject certificates
        # not trusted by the default CA bundle.
        http_client = httpx.Client(verify=False)
        _client = Groq(api_key=GROQ_API_KEY, http_client=http_client)
    return _client


def transcribe_voice(audio_bytes: bytes) -> str | None:
    """Transcribe Telegram OGG OPUS voice message using Groq Whisper.

    Telegram sends voice as OGG OPUS. We pass it with the .ogg extension so
    Whisper accepts it. Language auto-detection is used instead of locking to
    Chinese so multilingual input works correctly.
    """
    try:
        audio_file = io.BytesIO(audio_bytes)
        audio_file.name = "voice.ogg"
        response = _get_client().audio.transcriptions.create(
            file=audio_file,
            model="whisper-large-v3",
            # Do not set language= — let Whisper auto-detect for multilingual support
        )
        text = response.text.strip()
        logger.debug("[speech] Whisper transcription: %r", text)
        return text if text else None
    except Exception as e:
        logger.error("[speech] transcribe_voice failed: %s: %s", type(e).__name__, e)
        return None
