CREATE TABLE IF NOT EXISTS public.streamlit_sessions (
    session_id TEXT PRIMARY KEY,
    messages JSONB NOT NULL DEFAULT '[]'::jsonb,
    entity_state JSONB NOT NULL DEFAULT '{}'::jsonb,
    lead_score INTEGER NOT NULL DEFAULT 0,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
