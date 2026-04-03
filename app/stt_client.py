"""STT client for Sarvam AI."""

import httpx

from app.config import SARVAM_API_KEY


def _extract_confidence(payload: dict):
    """Extract confidence from common Sarvam response shapes.

    Returns None when confidence is not provided.
    """
    if not isinstance(payload, dict):
        return None

    # Common flat format.
    conf = payload.get("confidence")
    if conf is not None:
        return float(conf)

    # Nested alternatives seen in some STT APIs.
    if isinstance(payload.get("result"), dict):
        result_conf = payload["result"].get("confidence")
        if result_conf is not None:
            return float(result_conf)

    segments = payload.get("segments")
    if isinstance(segments, list) and segments:
        seg_conf = segments[0].get("confidence") if isinstance(segments[0], dict) else None
        if seg_conf is not None:
            return float(seg_conf)

    return None


async def transcribe_audio(audio_bytes: bytes, language_code: str = "hi-IN") -> dict:
    """Transcribe audio and return transcript metadata."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            "https://api.sarvam.ai/speech-to-text",
            headers={"api-subscription-key": SARVAM_API_KEY},
            files={"file": ("audio.wav", audio_bytes, "audio/wav")},
            data={"language_code": language_code},
        )
        response.raise_for_status()
        data = response.json()

    transcript = data.get("transcript", "")
    language = data.get("language_code", language_code[:2])
    confidence = _extract_confidence(data)

    return {
        "transcript": transcript,
        "language_code": language,
        "confidence": confidence,
    }
