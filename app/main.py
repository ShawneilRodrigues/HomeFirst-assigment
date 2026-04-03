"""FastAPI entry point with AgentOS integration."""

import base64

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import JSONResponse

from agno.os import AgentOS
from app.orchestrator import VoiceOrchestrator

app = FastAPI(title="HomeFirst Loan Counselor API", version="1.0.0")
orchestrator = VoiceOrchestrator()


def _detect_language_code(text: str) -> str:
    for ch in text:
        code = ord(ch)
        if 2944 <= code <= 3071:
            return "ta"
        if 2304 <= code <= 2431:
            return "hi"
    return "en"


@app.get("/health")
async def health() -> dict:
    return {"status": "healthy", "service": "homefirst-loan-counselor"}


@app.post("/api/voice")
async def voice_endpoint(
    audio: UploadFile = File(...),
    session_id: str = Form(...),
    user_id: str = Form(default="anonymous"),
):
    """Voice endpoint returning transcript, text, and synthesized audio."""
    audio_bytes = await audio.read()
    result = await orchestrator.process_voice_turn(audio_bytes=audio_bytes, session_id=session_id, user_id=user_id)
    audio_b64 = base64.b64encode(result["audio_bytes"]).decode("utf-8")

    return JSONResponse(
        {
            "transcript": result["transcript"],
            "response_text": result["response_text"],
            "audio_base64": audio_b64,
            "entity_state": result["entity_state"],
            "lead_score": result["lead_score"],
            "handoff_triggered": result["handoff_triggered"],
            "tool_called": result["tool_called"],
            "confidence": result["confidence"],
        }
    )


@app.post("/api/text")
async def text_endpoint(
    message: str = Form(...),
    session_id: str = Form(...),
    user_id: str = Form(default="anonymous"),
):
    """Text endpoint for quick testing without voice capture."""
    agent = orchestrator.agent
    response = agent.run(message, session_id=session_id, user_id=user_id)
    try:
        state = agent.get_session_state(session_id=session_id) or {}
    except Exception:
        state = dict(getattr(agent, "session_state", {}) or {})

    if not state.get("locked_language"):
        state["locked_language"] = _detect_language_code(message)
        agent.session_state["locked_language"] = state["locked_language"]

    from app.lead_scorer import compute_lead_score, should_handoff

    score = compute_lead_score(state, message)
    return JSONResponse(
        {
            "response_text": response.content,
            "entity_state": state,
            "lead_score": score,
            "handoff_triggered": should_handoff(score),
        }
    )


agent_os = AgentOS(agents=[orchestrator.agent], base_app=app)
app = agent_os.get_app()
