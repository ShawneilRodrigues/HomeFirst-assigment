"""Streamlit UI - Conversation + Debug Panel."""
import base64
import hashlib
import json
import os
import uuid

import httpx
import psycopg
import streamlit as st
from dotenv import load_dotenv

st.set_page_config(page_title="HomeFirst Loan Counselor", layout="wide")
load_dotenv()

API_URL = "http://localhost:8000"
DATABASE_URL = os.getenv("DATABASE_URL", "")
VOICE_TIMEOUT = httpx.Timeout(connect=10.0, read=180.0, write=60.0, pool=10.0)
TEXT_TIMEOUT = httpx.Timeout(connect=10.0, read=90.0, write=30.0, pool=10.0)


def _normalize_db_url(url: str) -> str:
    if url.startswith("postgresql+psycopg://"):
        return url.replace("postgresql+psycopg://", "postgresql://", 1)
    return url


def _ensure_persistence_table() -> None:
    db_url = _normalize_db_url(DATABASE_URL)
    if not db_url:
        return
    with psycopg.connect(db_url, connect_timeout=5) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS public.streamlit_sessions (
                    session_id TEXT PRIMARY KEY,
                    messages JSONB NOT NULL DEFAULT '[]'::jsonb,
                    entity_state JSONB NOT NULL DEFAULT '{}'::jsonb,
                    lead_score INTEGER NOT NULL DEFAULT 0,
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                """
            )
        conn.commit()


def _load_persisted_session(session_id: str):
    db_url = _normalize_db_url(DATABASE_URL)
    if not db_url:
        return None
    with psycopg.connect(db_url, connect_timeout=5) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT messages, entity_state, lead_score
                FROM public.streamlit_sessions
                WHERE session_id = %s
                """,
                (session_id,),
            )
            row = cur.fetchone()
            if not row:
                return None

    def _json_value(v):
        if isinstance(v, (dict, list)):
            return v
        return json.loads(v)

    return {
        "messages": _json_value(row[0]),
        "entity_state": _json_value(row[1]),
        "lead_score": int(row[2] or 0),
    }


def _save_persisted_session() -> None:
    db_url = _normalize_db_url(DATABASE_URL)
    if not db_url:
        return
    with psycopg.connect(db_url, connect_timeout=5) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO public.streamlit_sessions (session_id, messages, entity_state, lead_score, updated_at)
                VALUES (%s, %s::jsonb, %s::jsonb, %s, NOW())
                ON CONFLICT (session_id)
                DO UPDATE SET
                    messages = EXCLUDED.messages,
                    entity_state = EXCLUDED.entity_state,
                    lead_score = EXCLUDED.lead_score,
                    updated_at = NOW();
                """,
                (
                    st.session_state.session_id,
                    json.dumps(st.session_state.messages),
                    json.dumps(st.session_state.entity_state),
                    int(st.session_state.lead_score),
                ),
            )
        conn.commit()


def _save_current_to_local() -> None:
    st.session_state.local_sessions[st.session_state.session_id] = {
        "messages": list(st.session_state.messages),
        "entity_state": dict(st.session_state.entity_state),
        "lead_score": int(st.session_state.lead_score),
        "last_voice_fingerprint": st.session_state.last_voice_fingerprint,
    }


def _load_local_session(session_id: str):
    return st.session_state.local_sessions.get(session_id)


def _list_persisted_sessions(limit: int = 30):
    db_url = _normalize_db_url(DATABASE_URL)
    if not db_url:
        return []
    with psycopg.connect(db_url, connect_timeout=5) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT session_id, messages, updated_at
                FROM public.streamlit_sessions
                ORDER BY updated_at DESC
                LIMIT %s
                """,
                (limit,),
            )
            rows = cur.fetchall()

    sessions = []
    for session_id, messages, updated_at in rows:
        if isinstance(messages, list):
            parsed_messages = messages
        else:
            parsed_messages = json.loads(messages)

        preview = "New chat"
        for item in parsed_messages:
            if isinstance(item, dict) and item.get("role") == "user" and item.get("content"):
                preview = str(item["content"]).strip().replace("\n", " ")[:40]
                break

        sessions.append(
            {
                "session_id": session_id,
                "preview": preview,
                "updated_at": updated_at,
            }
        )
    return sessions


def _switch_session(session_id: str) -> None:
    _save_current_to_local()
    st.session_state.session_id = session_id
    st.session_state.last_voice_fingerprint = None
    persisted = None
    if st.session_state.persistence_status == "Connected":
        try:
            persisted = _load_persisted_session(session_id)
        except Exception:
            st.session_state.persistence_status = "Unavailable"

    if persisted:
        st.session_state.messages = persisted["messages"]
        st.session_state.entity_state = persisted["entity_state"]
        st.session_state.lead_score = persisted["lead_score"]
    else:
        local = _load_local_session(session_id)
        if local:
            st.session_state.messages = local["messages"]
            st.session_state.entity_state = local["entity_state"]
            st.session_state.lead_score = local["lead_score"]
            st.session_state.last_voice_fingerprint = local.get("last_voice_fingerprint")
        else:
            st.session_state.messages = []
            st.session_state.entity_state = {}
            st.session_state.lead_score = 0
            st.session_state.last_voice_fingerprint = None


def _new_chat() -> None:
    _save_current_to_local()
    new_id = str(uuid.uuid4())
    st.session_state.local_sessions[new_id] = {
        "messages": [],
        "entity_state": {},
        "lead_score": 0,
        "last_voice_fingerprint": None,
    }
    _switch_session(new_id)


def _post_voice(audio_bytes: bytes):
    try:
        resp = httpx.post(
            f"{API_URL}/api/voice",
            files={"audio": ("voice.wav", audio_bytes, "audio/wav")},
            data={
                "session_id": st.session_state.session_id,
                "user_id": "streamlit_user",
            },
            timeout=VOICE_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json()
    except httpx.ReadTimeout:
        st.error("Voice response timed out. Please retry or use text input.")
    except httpx.HTTPError as exc:
        st.error(f"Voice request failed: {exc}")
    return None


def _post_text(user_input: str):
    try:
        resp = httpx.post(
            f"{API_URL}/api/text",
            data={
                "message": user_input,
                "session_id": st.session_state.session_id,
                "user_id": "streamlit_user",
            },
            timeout=TEXT_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json()
    except httpx.ReadTimeout:
        st.error("Text response timed out. Please retry in a moment.")
    except httpx.HTTPError as exc:
        st.error(f"Text request failed: {exc}")
    return None

if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if "messages" not in st.session_state:
    st.session_state.messages = []
if "entity_state" not in st.session_state:
    st.session_state.entity_state = {}
if "lead_score" not in st.session_state:
    st.session_state.lead_score = 0
if "last_voice_fingerprint" not in st.session_state:
    st.session_state.last_voice_fingerprint = None
if "persistence_status" not in st.session_state:
    st.session_state.persistence_status = "Not initialized"
if "persistence_loaded" not in st.session_state:
    st.session_state.persistence_loaded = False
if "session_selector" not in st.session_state:
    st.session_state.session_selector = ""
if "local_sessions" not in st.session_state:
    st.session_state.local_sessions = {}

if not st.session_state.persistence_loaded:
    try:
        _ensure_persistence_table()
        persisted = _load_persisted_session(st.session_state.session_id)
        if persisted:
            st.session_state.messages = persisted["messages"]
            st.session_state.entity_state = persisted["entity_state"]
            st.session_state.lead_score = persisted["lead_score"]
        st.session_state.persistence_status = "Connected"
    except Exception:
        st.session_state.persistence_status = "Unavailable"
    st.session_state.persistence_loaded = True

if st.session_state.session_id not in st.session_state.local_sessions:
    st.session_state.local_sessions[st.session_state.session_id] = {
        "messages": list(st.session_state.messages),
        "entity_state": dict(st.session_state.entity_state),
        "lead_score": int(st.session_state.lead_score),
        "last_voice_fingerprint": st.session_state.last_voice_fingerprint,
    }

session_rows = []
if st.session_state.persistence_status == "Connected":
    try:
        session_rows = _list_persisted_sessions(limit=30)
    except Exception:
        st.session_state.persistence_status = "Unavailable"

with st.sidebar:
    st.markdown(
        """
        <style>
        [data-testid="stSidebar"] .chat-block {
            border: 1px solid #e6e8ef;
            border-radius: 12px;
            padding: 10px 12px;
            background: #fafbff;
            margin-bottom: 10px;
        }
        [data-testid="stSidebar"] .chat-meta {
            font-size: 12px;
            color: #6b7280;
            margin-top: 2px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.header("Chats")
    st.markdown(
        f"<div class='chat-block'><div><strong>Active</strong>: {st.session_state.session_id[:8]}</div>"
        f"<div class='chat-meta'>Local sessions: {len(st.session_state.local_sessions)}</div></div>",
        unsafe_allow_html=True,
    )
    if st.button("+ New Chat", use_container_width=True):
        _new_chat()
        st.rerun()

    options = [st.session_state.session_id]
    labels = {st.session_state.session_id: f"Current: {st.session_state.session_id[:8]}"}

    for sid, local in st.session_state.local_sessions.items():
        if sid not in options:
            options.append(sid)
            preview = "New chat"
            for item in local.get("messages", []):
                if isinstance(item, dict) and item.get("role") == "user" and item.get("content"):
                    preview = str(item["content"]).strip().replace("\n", " ")[:40]
                    break
            labels[sid] = f"{preview} ({sid[:8]})"

    for row in session_rows:
        sid = row["session_id"]
        if sid not in options:
            options.append(sid)
            labels[sid] = f"{row['preview']} ({sid[:8]})"

    if st.session_state.session_selector not in options:
        st.session_state.session_selector = st.session_state.session_id

    selected_session = st.radio(
        "Switch chat",
        options=options,
        format_func=lambda x: labels.get(x, x),
        key="session_selector",
    )

    if selected_session != st.session_state.session_id:
        _switch_session(selected_session)
        st.rerun()

    st.caption("Keep talking in the same chat, or switch chats anytime.")

left_col, right_col = st.columns([7, 3])

with left_col:
    st.title("HomeFirst Loan Counselor")
    st.caption("Voice-first AI agent for home loan counseling")

    action_col_1, action_col_2 = st.columns([1, 2])
    with action_col_1:
        if st.button("Start New Chat", use_container_width=True):
            _new_chat()
            st.rerun()
    with action_col_2:
        st.caption(f"Active Session: {st.session_state.session_id[:8]}")

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    voice_input = st.audio_input("Speak your message", sample_rate=16000)
    user_input = st.chat_input("Type your message or use voice...")

    if voice_input is not None:
        audio_bytes = voice_input.getvalue()
        fingerprint = hashlib.sha256(audio_bytes).hexdigest()

        if fingerprint != st.session_state.last_voice_fingerprint:
            st.session_state.last_voice_fingerprint = fingerprint

            with st.spinner("Priya is listening and responding..."):
                data = _post_voice(audio_bytes)

            if not data:
                st.session_state.last_voice_fingerprint = None
                st.stop()

            transcript = data.get("transcript", "")
            response_text = data.get("response_text", "")
            response_audio = base64.b64decode(data.get("audio_base64", ""))

            if transcript:
                st.session_state.messages.append({"role": "user", "content": transcript})
                with st.chat_message("user"):
                    st.write(transcript)

            st.session_state.messages.append({"role": "assistant", "content": response_text})
            st.session_state.entity_state = data.get("entity_state", {})
            st.session_state.lead_score = data.get("lead_score", 0)
            _save_current_to_local()
            try:
                _save_persisted_session()
                st.session_state.persistence_status = "Connected"
            except Exception:
                st.session_state.persistence_status = "Unavailable"

            with st.chat_message("assistant"):
                st.write(response_text)
                if response_audio:
                    st.audio(response_audio, format="audio/mp3")

            if data.get("handoff_triggered"):
                st.error("HANDOFF TRIGGERED: Routing to Human RM")

    if user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.write(user_input)

        with st.spinner("Priya is thinking..."):
            data = _post_text(user_input)

        if not data:
            st.stop()

        response_text = data["response_text"]
        st.session_state.messages.append({"role": "assistant", "content": response_text})
        st.session_state.entity_state = data.get("entity_state", {})
        st.session_state.lead_score = data.get("lead_score", 0)
        _save_current_to_local()
        try:
            _save_persisted_session()
            st.session_state.persistence_status = "Connected"
        except Exception:
            st.session_state.persistence_status = "Unavailable"

        with st.chat_message("assistant"):
            st.write(response_text)

        if data.get("audio_base64"):
            st.audio(base64.b64decode(data["audio_base64"]), format="audio/mp3")

        if data.get("handoff_triggered"):
            st.error("HANDOFF TRIGGERED: Routing to Human RM")

with right_col:
    st.subheader("Debug Panel")

    st.metric("Session Persistence", st.session_state.persistence_status)

    state = st.session_state.entity_state
    lang = state.get("locked_language") or "Not detected"
    st.metric("Language", f"{lang} - {'LOCKED' if lang else 'detecting...'}")

    score = st.session_state.lead_score
    color = "RED" if score < 5 else "AMBER" if score < 8 else "GREEN"
    st.metric("Lead Score", f"{color} {score}/10")
    st.progress(score / 10)

    st.subheader("Extracted Entities")
    entity_display = {
        "Monthly Income": state.get("monthly_income"),
        "Property Value": state.get("property_value"),
        "Loan Requested": state.get("loan_amount_requested"),
        "Employment": state.get("employment_status"),
        "Existing EMIs": state.get("existing_emis"),
        "Tenure (months)": state.get("tenure_months"),
    }
    for k, v in entity_display.items():
        st.text(f"{k}: {v if v is not None else '-'}")

    st.subheader("Tool Execution")
    st.text(f"Tool Called: {state.get('tool_called', False)}")
    if state.get("eligibility_result"):
        st.json(state["eligibility_result"])

    if state.get("handoff_triggered"):
        st.error("HANDOFF TRIGGERED")
