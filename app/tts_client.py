"""TTS client for Sarvam AI."""

import httpx

from app.config import SARVAM_API_KEY, SARVAM_TTS_MODEL, SARVAM_TTS_SPEAKER

LANGUAGE_MAP = {
    "hi": "hi-IN",
    "en": "en-IN",
    "mr": "mr-IN",
    "ta": "ta-IN",
}


async def synthesize_speech(text: str, language: str = "hi") -> bytes:
    """Convert text into speech bytes."""
    target_language_code = LANGUAGE_MAP.get(language, "hi-IN")
    payload = {
        "text": text,
        "target_language_code": target_language_code,
        "speaker": SARVAM_TTS_SPEAKER,
        "model": SARVAM_TTS_MODEL,
        "pace": 1.1,
        "speech_sample_rate": 22050,
        "output_audio_codec": "mp3",
        "enable_preprocessing": True,
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(
            "https://api.sarvam.ai/text-to-speech/stream",
            headers={
                "api-subscription-key": SARVAM_API_KEY,
                "Content-Type": "application/json",
            },
            json=payload,
        )
        response.raise_for_status()
        return response.content
