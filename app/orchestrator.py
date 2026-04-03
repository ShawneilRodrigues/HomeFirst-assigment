"""Orchestrates STT, agent response, lead scoring, and TTS."""

from app.counselor_agent import create_counselor_agent
from app.lead_scorer import compute_lead_score, should_handoff
from app.stt_client import transcribe_audio
from app.tts_client import synthesize_speech


class VoiceOrchestrator:
    def __init__(self) -> None:
        self.agent = create_counselor_agent()

    async def process_voice_turn(self, audio_bytes: bytes, session_id: str, user_id: str = "anonymous") -> dict:
        """Process one end-to-end voice turn."""
        current_lang = self.agent.session_state.get("locked_language") or "hi"
        lang_map = {"hi": "hi-IN", "en": "en-IN", "mr": "mr-IN", "ta": "ta-IN"}
        stt_result = await transcribe_audio(audio_bytes, language_code=lang_map.get(current_lang, "hi-IN"))

        transcript = stt_result["transcript"]
        confidence = stt_result["confidence"]

        # Fallback only when transcript is empty or confidence is explicitly low.
        if not transcript or (confidence is not None and confidence < 0.7):
            fallback_text = {
                "hi": "Maaf kijiye, mujhe aapki baat samajh nahi aayi. Kya aap dobara bol sakte hain?",
                "en": "Sorry, I did not catch that. Could you please repeat?",
                "mr": "Maaf kara, mala samajale nahi. Krupaya punha sanga.",
                "ta": "Mannikkavum, enakku puriyavillai. Thayavu seithu meendum sollungal.",
            }.get(current_lang, "Sorry, I did not catch that. Could you please repeat?")

            audio = await synthesize_speech(fallback_text, current_lang)
            return {
                "transcript": transcript,
                "response_text": fallback_text,
                "audio_bytes": audio,
                "entity_state": self.agent.session_state,
                "lead_score": self.agent.session_state.get("lead_score", 0),
                "handoff_triggered": False,
                "tool_called": False,
                "confidence": confidence,
            }

        if not self.agent.session_state.get("locked_language"):
            detected_lang = (stt_result["language_code"] or "hi")[:2]
            self.agent.session_state["locked_language"] = detected_lang

        response = self.agent.run(transcript, session_id=session_id, user_id=user_id)
        response_text = response.content

        try:
            state = self.agent.get_session_state(session_id=session_id) or {}
        except Exception:
            state = dict(getattr(self.agent, "session_state", {}) or {})
        state["turn_count"] = state.get("turn_count", 0) + 1

        lead_score = compute_lead_score(state, transcript)
        state["lead_score"] = lead_score
        handoff = should_handoff(lead_score)
        state["handoff_triggered"] = handoff

        locked_lang = state.get("locked_language", "hi")
        audio = await synthesize_speech(response_text, locked_lang)

        return {
            "transcript": transcript,
            "response_text": response_text,
            "audio_bytes": audio,
            "entity_state": state,
            "lead_score": lead_score,
            "handoff_triggered": handoff,
            "tool_called": state.get("tool_called", False),
            "confidence": confidence,
        }
